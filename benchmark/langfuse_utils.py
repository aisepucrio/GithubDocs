"""
Utilitarios compartilhados para o pipeline de avaliacao com Langfuse.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from dotenv import load_dotenv
from langfuse import Langfuse, get_client

from src.load_configuration.conf_structures import (
    BaseAppConfig,
    OrchestrationStep,
    OutputInfo,
    TargetInfo,
)

from .test_configs import TEST_TYPE_PROMPTS, TestType

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATASET_NAME = "gh-docs-eval"
DEFAULT_EXPERIMENT_NAME = "gh-docs-experiment"
DEFAULT_REQUIRED_SCORES = ("doc_quality", "hallucination", "consistency")
DEFAULT_MODEL_NAME = "gemini-2.5-flash"
DEFAULT_TEMPERATURE = 0.2
DEFAULT_TEST_TYPE = TestType.README_UPDATE.value
DEFAULT_IGNORE_FILES = [
    "IGNORED_PRESET",
    "RELEASE_NOTES.md",
    "CHANGELOG.md",
    "README.md",
]
CSV_COLUMN_ALIASES = {
    "description": ["description", "Descrição do Teste", "Descricao do Teste"],
    "repo_path": ["repo_path", "Repo"],
    "branch_name": ["branch_name", "Branch", "Branch Name", "branch"],
    "commits": ["commits", "Commits"],
    "commit_mixed": ["commit_mixed", "Commit Mixed"],
    "model_name": ["model_name", "Modelo"],
    "temperature": ["temperature", "Temperatura"],
    "type": ["type", "test_type", "Tipo"],
    "project_description": ["project_description", "Project Description"],
    "github_repo_name": ["github_repo_name", "GitHub Repo Name"],
    "ignore_files": ["ignore_files", "Ignore Files"],
    "precomputed_output": ["precomputed_output", "Conteúdo Output", "Conteudo Output"],
    "prompt_content": ["prompt_content", "Prompt"],
    "error_message": ["error_message", "Erro"],
    "timestamp": ["timestamp", "Timestamp"],
}
LANGFUSE_OUTPUT_DIR = PROJECT_ROOT / "output" / "langfuse_eval"
LANGFUSE_LOG_DIR = PROJECT_ROOT / "logs" / "langfuse_eval"


def load_project_env() -> None:
    """Carrega o .env do projeto e garante os diretorios de saida."""
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    LANGFUSE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    LANGFUSE_LOG_DIR.mkdir(parents=True, exist_ok=True)


def require_langfuse_client() -> Langfuse:
    """Retorna um cliente Langfuse autenticado."""
    load_project_env()
    client = get_client()

    if not hasattr(client, "api"):
        raise RuntimeError(
            "Langfuse nao esta configurado. Defina LANGFUSE_PUBLIC_KEY e "
            "LANGFUSE_SECRET_KEY no .env ou no ambiente."
        )

    return client


def get_langfuse_base_url() -> str:
    return (
        os.getenv("LANGFUSE_BASE_URL")
        or os.getenv("LANGFUSE_HOST")
        or "https://cloud.langfuse.com"
    )


def normalize_scalar(value: Any) -> Any:
    """Converte NaN/strings vazias para None sem perder tipos simples."""
    if value is None:
        return None

    try:
        if isinstance(value, float) and value != value:
            return None
    except TypeError:
        pass

    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    return value


def parse_bool(value: Any, default: bool = False) -> bool:
    normalized = normalize_scalar(value)
    if normalized is None:
        return default

    if isinstance(normalized, bool):
        return normalized

    return str(normalized).strip().lower() in {
        "1",
        "true",
        "yes",
        "y",
        "sim",
        "s",
    }


def parse_temperature(value: Any, default: float = DEFAULT_TEMPERATURE) -> float:
    normalized = normalize_scalar(value)
    if normalized is None:
        return default
    if isinstance(normalized, str):
        normalized = normalized.replace(",", ".")
    return float(normalized)


def parse_commits(value: Any) -> tuple[list[str], str]:
    normalized = normalize_scalar(value)
    if normalized is None:
        raise ValueError("A coluna 'commits' nao pode estar vazia.")

    if isinstance(normalized, list):
        commits = [str(commit).strip() for commit in normalized if str(commit).strip()]
    else:
        commits = [part.strip() for part in str(normalized).split(",") if part.strip()]

    if not commits:
        raise ValueError("A coluna 'commits' nao pode estar vazia.")

    return commits, ", ".join(commits)


def canonicalize_csv_row(row: dict[str, Any]) -> dict[str, Any]:
    canonical = {key: normalize_scalar(value) for key, value in row.items()}

    for canonical_name, aliases in CSV_COLUMN_ALIASES.items():
        if canonical.get(canonical_name) is not None:
            continue

        for alias in aliases:
            if alias in canonical and canonical[alias] is not None:
                canonical[canonical_name] = canonical[alias]
                break

    return canonical


def parse_test_type(value: Any, default: str = DEFAULT_TEST_TYPE) -> TestType:
    if isinstance(value, TestType):
        return value

    normalized = normalize_scalar(value) or default
    if isinstance(normalized, TestType):
        return normalized
    return TestType(str(normalized))


def parse_ignore_files(value: Any) -> list[str]:
    normalized = normalize_scalar(value)
    if normalized is None:
        return list(DEFAULT_IGNORE_FILES)

    if isinstance(normalized, list):
        items = [str(item).strip() for item in normalized if str(item).strip()]
        return items or list(DEFAULT_IGNORE_FILES)

    raw = str(normalized).strip()
    if raw.startswith("["):
        parsed = json.loads(raw)
        if not isinstance(parsed, list):
            raise ValueError("ignore_files em JSON deve ser uma lista.")
        return [str(item).strip() for item in parsed if str(item).strip()]

    items = [part.strip() for part in raw.split(",") if part.strip()]
    return items or list(DEFAULT_IGNORE_FILES)


def resolve_repo_path(repo_path: str) -> str:
    path = Path(repo_path)
    if path.is_absolute():
        return str(path)
    return str((PROJECT_ROOT / path).resolve())


def slugify(value: str) -> str:
    allowed = []
    for char in value.lower():
        if char.isalnum():
            allowed.append(char)
        else:
            allowed.append("-")

    slug = "".join(allowed)
    while "--" in slug:
        slug = slug.replace("--", "-")

    return slug.strip("-") or "run"


def build_dataset_item_id(dataset_name: str, payload: dict[str, Any]) -> str:
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=True, default=str).encode(
            "utf-8"
        )
    ).hexdigest()
    return f"{slugify(dataset_name)}-{digest[:24]}"


def parse_dataset_version(version: str | None) -> datetime | None:
    if not version:
        return None

    normalized = version.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def serialize_for_csv(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def score_value_to_python(score: Any) -> Any:
    data_type = getattr(score, "data_type", None)
    if data_type == "NUMERIC":
        return getattr(score, "value", None)
    if data_type in {"BOOLEAN", "CATEGORICAL"}:
        return getattr(score, "string_value", None) or getattr(score, "value", None)
    return getattr(score, "value", None)


def ensure_absolute_output_path(path: str | Path) -> Path:
    output_path = Path(path)
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return output_path


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def iter_pages(fetch_page: Any) -> Iterable[Any]:
    page = 1
    while True:
        response = fetch_page(page)
        for item in response.data:
            yield item

        if response.meta.total_pages <= page:
            break
        page += 1


def build_pipeline_config(
    *,
    task: str,
    repo_path: str,
    branch_name: str,
    commits: list[str],
    model_name: str,
    temperature: float,
    test_type: TestType,
    output_file_name: str,
    project_description: str | None = None,
    github_repo_name: str | None = None,
    ignore_files: list[str] | None = None,
) -> BaseAppConfig:
    prompt_variables: dict[str, str] = {
        "name": task,
        "repo": repo_path,
    }

    if test_type == TestType.README_CREATE and project_description:
        prompt_variables["repo_description"] = project_description

    return BaseAppConfig(
        target_info=TargetInfo(
            repo_path=resolve_repo_path(repo_path),
            branch_name=branch_name,
            commit_list=commits,
            ignore_files=ignore_files or list(DEFAULT_IGNORE_FILES),
            github_repo_name=github_repo_name,
        ),
        output_info=OutputInfo(
            result_path=str(LANGFUSE_OUTPUT_DIR),
            log_path=str(LANGFUSE_LOG_DIR),
            result_file_name=output_file_name,
        ),
        orchestration_steps=[
            OrchestrationStep(
                step=1,
                model_name=model_name,
                temperature=temperature,
                prompt_file=TEST_TYPE_PROMPTS[test_type],
                template_path=str((PROJECT_ROOT / "prompt").resolve()),
                prompt_variables=prompt_variables,
                tools=[],
            )
        ],
    )
