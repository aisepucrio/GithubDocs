"""
Configure Langfuse score configs and annotation queue for GithubDocs.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .langfuse_annotation import (
    MANUAL_ANNOTATION_QUEUE_NAME,
    MANUAL_SCORE_CONFIGS,
    ensure_manual_annotation_queue,
    ensure_score_configs,
    fetch_annotation_queues,
    preferred_score_config_ids,
)
from .langfuse_utils import PROJECT_ROOT, require_langfuse_client


def _score_config_id(selection: Any) -> str:
    return selection.config.id if selection.config is not None else "<missing>"


def _score_config_status(selection: Any) -> str:
    if selection.created:
        return "created"
    if selection.config is None:
        return "missing"
    return "existing"


def _write_env_value(env_path: Path, key: str, value: str) -> None:
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()
    else:
        lines = []

    replacement = f"{key}={value}"
    updated = False
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            continue
        current_key = line.split("=", 1)[0].strip()
        if current_key == key:
            lines[index] = replacement
            updated = True
            break

    if not updated:
        if lines and lines[-1].strip():
            lines.append("")
        lines.append(replacement)

    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _queue_score_config_ids(queue: Any) -> list[str]:
    ids = getattr(queue, "score_config_ids", None)
    if ids is not None:
        return list(ids)
    return [
        cfg.id
        for cfg in getattr(queue, "score_configs", None) or []
        if getattr(cfg, "id", None)
    ]


def _print_summary(
    *,
    selections: dict[str, Any],
    queue: Any | None,
    dry_run: bool,
    env_path: Path,
    update_env: bool,
) -> None:
    print("GithubDocs Langfuse manual annotation setup")
    print(f"Mode: {'dry-run' if dry_run else 'apply'}")
    print("")
    print("Score configs:")

    for spec in MANUAL_SCORE_CONFIGS:
        selection = selections[spec["name"]]
        duplicate_ids = [duplicate.id for duplicate in selection.duplicates]
        duplicate_suffix = (
            f" | duplicate ids: {', '.join(duplicate_ids)}"
            if duplicate_ids
            else ""
        )
        print(
            f"- {selection.name}: {_score_config_status(selection)} "
            f"({ _score_config_id(selection) }){duplicate_suffix}"
        )

    print("")
    if queue is None:
        print(f"Annotation queue: would create '{MANUAL_ANNOTATION_QUEUE_NAME}'")
    else:
        print(f"Annotation queue: {queue.name} ({queue.id})")
        print(f"Score config ids: {', '.join(_queue_score_config_ids(queue))}")

    print("")
    if dry_run:
        print(f".env update: would set LANGFUSE_ANNOTATION_QUEUE_ID in {env_path}")
    elif update_env and queue is not None:
        print(f".env update: LANGFUSE_ANNOTATION_QUEUE_ID set in {env_path}")
    else:
        print(".env update: skipped")


def configure_langfuse_manual_annotation(
    *,
    dry_run: bool,
    queue_name: str,
    env_path: Path,
    update_env: bool,
) -> dict[str, Any]:
    client = require_langfuse_client()
    preferred_ids = preferred_score_config_ids(client)
    selections = ensure_score_configs(
        client,
        dry_run=dry_run,
        preferred_ids=preferred_ids,
    )
    queue = ensure_manual_annotation_queue(
        client,
        selections,
        queue_name=queue_name,
        dry_run=dry_run,
    )

    if not dry_run and update_env and queue is not None:
        _write_env_value(env_path, "LANGFUSE_ANNOTATION_QUEUE_ID", queue.id)

    _print_summary(
        selections=selections,
        queue=queue,
        dry_run=dry_run,
        env_path=env_path,
        update_env=update_env,
    )

    return {
        "queue_id": getattr(queue, "id", None),
        "score_config_ids": {
            name: selection.config.id if selection.config is not None else None
            for name, selection in selections.items()
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Configure GithubDocs manual annotation in Langfuse."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Inspect the current Langfuse setup without creating resources.",
    )
    parser.add_argument(
        "--queue-name",
        default=MANUAL_ANNOTATION_QUEUE_NAME,
        help=f"Annotation queue name (default: {MANUAL_ANNOTATION_QUEUE_NAME})",
    )
    parser.add_argument(
        "--env-path",
        default=str(PROJECT_ROOT / ".env"),
        help="Path to the .env file to update.",
    )
    parser.add_argument(
        "--no-update-env",
        action="store_true",
        help="Do not write LANGFUSE_ANNOTATION_QUEUE_ID to .env.",
    )
    parser.add_argument(
        "--list-queues",
        action="store_true",
        help="List existing annotation queues and exit.",
    )
    args = parser.parse_args()

    if args.list_queues:
        client = require_langfuse_client()
        for queue in fetch_annotation_queues(client):
            print(
                f"{queue.id}\t{queue.name}\t"
                f"{','.join(_queue_score_config_ids(queue))}"
            )
        return 0

    configure_langfuse_manual_annotation(
        dry_run=args.dry_run,
        queue_name=args.queue_name,
        env_path=Path(args.env_path),
        update_env=not args.no_update_env,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
