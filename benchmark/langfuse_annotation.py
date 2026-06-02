"""
Helpers for GithubDocs manual annotation setup in Langfuse.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

from .langfuse_utils import iter_pages

logger = logging.getLogger(__name__)

MANUAL_ANNOTATION_QUEUE_NAME = "GithubDocs Avaliação Manual"
LEGACY_ANNOTATION_QUEUE_NAME = "Métricas de Avaliação"

MANUAL_SCORE_CONFIGS = [
    {
        "name": "clareza",
        "data_type": "NUMERIC",
        "min_value": 0.0,
        "max_value": 5.0,
        "description": "Human annotation score for output clarity.",
    },
    {
        "name": "completude",
        "data_type": "NUMERIC",
        "min_value": 0.0,
        "max_value": 5.0,
        "description": "Human annotation score for documentation completeness.",
    },
    {
        "name": "concisão",
        "data_type": "NUMERIC",
        "min_value": 0.0,
        "max_value": 5.0,
        "description": "Human annotation score for concision.",
    },
    {
        "name": "corretude",
        "data_type": "NUMERIC",
        "min_value": 0.0,
        "max_value": 5.0,
        "description": "Human annotation score for factual and technical correctness.",
    },
    {
        "name": "observação",
        "data_type": "NUMERIC",
        "min_value": 0.0,
        "max_value": 5.0,
        "description": "Human annotation score for reviewer observation.",
    },
]

PROGRAMMATIC_SCORE_CONFIGS = [
    {
        "name": "sucesso",
        "data_type": "BOOLEAN",
        "description": "Programmatic success flag for the pipeline execution.",
    },
    {
        "name": "tempo",
        "data_type": "NUMERIC",
        "min_value": 0.0,
        "description": "Programmatic pipeline execution time in seconds.",
    },
]

ALL_GITHUBDOCS_SCORE_CONFIGS = [
    *MANUAL_SCORE_CONFIGS,
    *PROGRAMMATIC_SCORE_CONFIGS,
]


@dataclass(frozen=True)
class ScoreConfigSelection:
    """Resolved score config state for one score name."""

    name: str
    config: Any | None
    duplicates: tuple[Any, ...]
    created: bool = False


def get_annotation_queue_id(queue_id: str | None = None) -> str | None:
    return queue_id or os.environ.get("LANGFUSE_ANNOTATION_QUEUE_ID") or None


def fetch_score_configs(client: Any) -> list[Any]:
    return list(
        iter_pages(
            lambda page: client.api.score_configs.get(
                page=page,
                limit=100,
            )
        )
    )


def fetch_annotation_queues(client: Any) -> list[Any]:
    return list(
        iter_pages(
            lambda page: client.api.annotation_queues.list_queues(
                page=page,
                limit=100,
            )
        )
    )


def _is_archived(score_config: Any) -> bool:
    return bool(getattr(score_config, "is_archived", False))


def _score_config_ids(queue: Any) -> list[str]:
    ids = getattr(queue, "score_config_ids", None)
    if ids is not None:
        return list(ids)

    score_configs = getattr(queue, "score_configs", None) or []
    return [cfg.id for cfg in score_configs if getattr(cfg, "id", None)]


def _created_at(score_config: Any) -> Any:
    return getattr(score_config, "created_at", None)


def _matches_score_spec(score_config: Any, spec: dict[str, Any]) -> bool:
    if getattr(score_config, "name", None) != spec["name"]:
        return False
    if str(getattr(score_config, "data_type", "")) != spec["data_type"]:
        return False

    for key in ("min_value", "max_value"):
        expected = spec.get(key)
        actual = getattr(score_config, key, None)
        if expected is None:
            continue
        if actual is None or abs(float(actual) - float(expected)) > 1e-9:
            return False

    return True


def _canonical_score_config(
    candidates: list[Any],
    preferred_ids: set[str],
) -> Any | None:
    active = [cfg for cfg in candidates if not _is_archived(cfg)]
    if not active:
        return None

    preferred = [cfg for cfg in active if cfg.id in preferred_ids]
    if preferred:
        return sorted(preferred, key=_created_at)[-1]

    return sorted(active, key=_created_at)[-1]


def _score_config_create_kwargs(spec: dict[str, Any]) -> dict[str, Any]:
    kwargs = {
        "name": spec["name"],
        "data_type": spec["data_type"],
    }

    if spec.get("description"):
        kwargs["description"] = spec["description"]
    if spec["data_type"] == "NUMERIC":
        if spec.get("min_value") is not None:
            kwargs["min_value"] = spec["min_value"]
        if spec.get("max_value") is not None:
            kwargs["max_value"] = spec["max_value"]

    return kwargs


def find_annotation_queue_by_name(client: Any, queue_name: str) -> Any | None:
    for queue in fetch_annotation_queues(client):
        if getattr(queue, "name", None) == queue_name:
            return queue
    return None


def preferred_score_config_ids(client: Any) -> set[str]:
    queue = find_annotation_queue_by_name(client, LEGACY_ANNOTATION_QUEUE_NAME)
    if queue is None:
        return set()
    return set(_score_config_ids(queue))


def ensure_score_configs(
    client: Any,
    specs: list[dict[str, Any]] | None = None,
    *,
    dry_run: bool = False,
    preferred_ids: set[str] | None = None,
) -> dict[str, ScoreConfigSelection]:
    score_specs = specs or ALL_GITHUBDOCS_SCORE_CONFIGS
    preferred_ids = preferred_ids or preferred_score_config_ids(client)
    existing = fetch_score_configs(client)
    selections: dict[str, ScoreConfigSelection] = {}

    for spec in score_specs:
        matches = [cfg for cfg in existing if _matches_score_spec(cfg, spec)]
        canonical = _canonical_score_config(matches, preferred_ids)
        created = False

        if canonical is None and not dry_run:
            canonical = client.api.score_configs.create(
                **_score_config_create_kwargs(spec)
            )
            existing.append(canonical)
            created = True

        duplicates = tuple(
            cfg for cfg in matches if canonical is not None and cfg.id != canonical.id
        )
        selections[spec["name"]] = ScoreConfigSelection(
            name=spec["name"],
            config=canonical,
            duplicates=duplicates,
            created=created,
        )

    return selections


def ensure_manual_annotation_queue(
    client: Any,
    score_configs: dict[str, ScoreConfigSelection],
    *,
    queue_name: str = MANUAL_ANNOTATION_QUEUE_NAME,
    dry_run: bool = False,
) -> Any | None:
    score_config_ids = []
    for spec in MANUAL_SCORE_CONFIGS:
        selection = score_configs[spec["name"]]
        if selection.config is None:
            if dry_run:
                continue
            raise RuntimeError(f"Missing score config for {spec['name']}")
        score_config_ids.append(selection.config.id)

    desired_ids = set(score_config_ids)
    for queue in fetch_annotation_queues(client):
        if getattr(queue, "name", None) != queue_name:
            continue
        if set(_score_config_ids(queue)) == desired_ids:
            return queue

    if dry_run:
        return None

    return client.api.annotation_queues.create_queue(
        name=queue_name,
        description=(
            "Manual GithubDocs evaluation queue for clarity, completeness, "
            "concision, correctness, and reviewer observation."
        ),
        score_config_ids=score_config_ids,
    )


def _existing_queue_object_ids(client: Any, queue_id: str) -> set[str]:
    items = iter_pages(
        lambda page: client.api.annotation_queues.list_queue_items(
            queue_id,
            page=page,
            limit=100,
        )
    )
    return {item.object_id for item in items if getattr(item, "object_id", None)}


def enqueue_traces_for_annotation(
    client: Any,
    trace_ids: list[str],
    *,
    queue_id: str | None = None,
) -> dict[str, int | str | None]:
    resolved_queue_id = get_annotation_queue_id(queue_id)
    if not resolved_queue_id or not trace_ids:
        return {
            "queue_id": resolved_queue_id,
            "queued": 0,
            "skipped": 0,
            "failed": 0,
        }

    from langfuse.api.annotation_queues.types import AnnotationQueueObjectType

    existing_ids = _existing_queue_object_ids(client, resolved_queue_id)
    queued = 0
    skipped = 0
    failed = 0

    for trace_id in dict.fromkeys(trace_ids):
        if trace_id in existing_ids:
            skipped += 1
            continue

        try:
            client.api.annotation_queues.create_queue_item(
                queue_id=resolved_queue_id,
                object_id=trace_id,
                object_type=AnnotationQueueObjectType.TRACE,
            )
            existing_ids.add(trace_id)
            queued += 1
        except Exception:
            failed += 1
            logger.exception(
                "Failed to add trace %s to Langfuse annotation queue %s.",
                trace_id,
                resolved_queue_id,
            )

    return {
        "queue_id": resolved_queue_id,
        "queued": queued,
        "skipped": skipped,
        "failed": failed,
    }
