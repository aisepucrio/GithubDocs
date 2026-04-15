import os
import logging
from typing import Optional
from langfuse.langchain import CallbackHandler

_current_trace_id: Optional[str] = None
_langfuse_client = None

logger = logging.getLogger(__name__)


def set_current_trace_id(trace_id: str) -> None:
    """Define o trace_id ativo para que o CallbackHandler use como trace pai."""
    global _current_trace_id
    _current_trace_id = trace_id


def clear_current_trace_id() -> None:
    """Limpa o trace_id ativo após a conclusão de um benchmark."""
    global _current_trace_id
    _current_trace_id = None


def get_langfuse_client():
    """
    Retorna um cliente Langfuse singleton se as variáveis de ambiente estiverem
    configuradas. Caso contrário, retorna None.
    """
    global _langfuse_client
    if _langfuse_client is not None:
        return _langfuse_client

    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY")
    secret_key = os.environ.get("LANGFUSE_SECRET_KEY")

    if public_key and secret_key:
        try:
            if "LANGFUSE_BASE_URL" in os.environ and "LANGFUSE_HOST" not in os.environ:
                os.environ["LANGFUSE_HOST"] = os.environ["LANGFUSE_BASE_URL"]

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
    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY")
    secret_key = os.environ.get("LANGFUSE_SECRET_KEY")

    if public_key and secret_key:
        try:
            if "LANGFUSE_BASE_URL" in os.environ and "LANGFUSE_HOST" not in os.environ:
                os.environ["LANGFUSE_HOST"] = os.environ["LANGFUSE_BASE_URL"]

            kwargs = {}
            if _current_trace_id:
                kwargs["trace_id"] = _current_trace_id

            handler = CallbackHandler(**kwargs)
            return handler
        except Exception:
            logger.exception(
                "Failed to initialize Langfuse callback"
            )
            return None

    return None
