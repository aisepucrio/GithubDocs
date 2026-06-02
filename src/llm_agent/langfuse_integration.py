import logging
import os
from contextvars import ContextVar
from typing import Any, Optional

from langfuse.langchain import CallbackHandler

_current_trace_id: ContextVar[Optional[str]] = ContextVar(
    "githubdocs_langfuse_trace_id",
    default=None,
)
_langfuse_client = None

logger = logging.getLogger(__name__)

MAX_PROPAGATED_METADATA_LENGTH = 200


def set_current_trace_id(trace_id: str) -> None:
    """Set the active trace_id so CallbackHandler attaches spans to the parent trace."""
    _current_trace_id.set(trace_id)


def clear_current_trace_id() -> None:
    """Clear the active trace_id after a benchmark/run completes."""
    _current_trace_id.set(None)


def is_langfuse_configured() -> bool:
    """Return True when the minimum Langfuse credentials are available."""
    return bool(
        os.environ.get("LANGFUSE_PUBLIC_KEY")
        and os.environ.get("LANGFUSE_SECRET_KEY")
    )


def normalize_langfuse_environment() -> None:
    """Keep backwards compatibility with LANGFUSE_BASE_URL."""
    if "LANGFUSE_BASE_URL" in os.environ and "LANGFUSE_HOST" not in os.environ:
        os.environ["LANGFUSE_HOST"] = os.environ["LANGFUSE_BASE_URL"]


def _stringify_metadata_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (list, tuple, set)):
        rendered = ", ".join(str(item) for item in value if item is not None)
    else:
        rendered = str(value)
    rendered = rendered.strip()
    if not rendered:
        return None
    return rendered[:MAX_PROPAGATED_METADATA_LENGTH]


def safe_langfuse_metadata(metadata: dict[str, Any]) -> dict[str, str]:
    """
    Coerce propagated metadata to the Langfuse v4 string metadata contract.

    Langfuse v4 propagates these attributes to child observations; keeping values
    small and string-only avoids dropped metadata and accidental large payloads.
    """
    safe: dict[str, str] = {}
    for key, value in metadata.items():
        rendered = _stringify_metadata_value(value)
        if rendered is not None:
            safe[str(key)] = rendered
    return safe


def build_run_metadata(
    *,
    repo_path: str,
    branch_name: str,
    commit_list: list[str] | None,
    config_file: str | None,
    model_names: list[str],
    temperatures: list[float],
) -> dict[str, str]:
    return safe_langfuse_metadata(
        {
            "app": "GithubDocs",
            "repo_path": repo_path,
            "branch_name": branch_name,
            "commit_count": len(commit_list or []),
            "commit_list": commit_list or [],
            "config_file": config_file,
            "model_names": model_names,
            "temperatures": temperatures,
        }
    )


def build_run_tags(model_names: list[str], extra: list[str] | None = None) -> list[str]:
    tags = ["githubdocs", "manual-run"]
    tags.extend(model_names)
    if extra:
        tags.extend(extra)
    return [tag for tag in dict.fromkeys(str(tag) for tag in tags if tag)]


def get_langfuse_client():
    """Return a singleton Langfuse client when credentials are configured; otherwise None."""
    global _langfuse_client
    if _langfuse_client is not None:
        return _langfuse_client

    if is_langfuse_configured():
        try:
            normalize_langfuse_environment()
            from langfuse import Langfuse
            _langfuse_client = Langfuse()
            return _langfuse_client
        except Exception:
            logger.exception("Failed to initialize Langfuse client")

    return None


def get_langfuse_callback():
    """
    Initializes and returns the Langfuse CallbackHandler if the required
    environment variables are set. Otherwise, returns None.

    If a trace_id is currently active (set via set_current_trace_id), the
    callback will attach LLM spans as children of that trace, linking
    LangChain calls to the parent benchmark trace.
    """
    if is_langfuse_configured():
        try:
            normalize_langfuse_environment()
            kwargs = {}
            current_trace_id = _current_trace_id.get()
            if current_trace_id:
                kwargs["trace_context"] = {"trace_id": current_trace_id}

            handler = CallbackHandler(**kwargs)
            return handler
        except Exception:
            logger.exception(
                "Failed to initialize Langfuse callback"
            )
            return None

    return None


def append_langfuse_callback(config: dict | None = None) -> dict | None:
    """Append a Langfuse LangChain callback to a Runnable config if enabled."""
    callback = get_langfuse_callback()
    if callback is None:
        return config

    config = dict(config or {})
    callbacks = list(config.get("callbacks") or [])
    callbacks.append(callback)
    config["callbacks"] = callbacks
    return config
