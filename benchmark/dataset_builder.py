"""
Sincroniza um CSV de avaliacoes com um dataset do Langfuse.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd
from langfuse.api.commons.errors import NotFoundError

from .langfuse_utils import (
    DEFAULT_DATASET_NAME,
    DEFAULT_TEST_TYPE,
    build_dataset_item_id,
    canonicalize_csv_row,
    normalize_scalar,
    parse_bool,
    parse_commits,
    parse_ignore_files,
    parse_temperature,
    parse_test_type,
    require_langfuse_client,
)

REQUIRED_COLUMNS = ("description", "repo_path")


def _row_to_dataset_payload(
    *,
    dataset_name: str,
    row: dict[str, Any],
    row_number: int,
    csv_path: Path,
    default_test_type: str,
) -> dict[str, Any]:
    row = canonicalize_csv_row(row)

    for column in REQUIRED_COLUMNS:
        if normalize_scalar(row.get(column)) is None:
            raise ValueError(
                f"Linha {row_number}: coluna obrigatoria ausente: {column}"
            )

    precomputed_output = normalize_scalar(row.get("precomputed_output"))
    commits_value = row.get("commits")
    branch_name = normalize_scalar(row.get("branch_name"))

    if commits_value is not None:
        commits, commits_raw = parse_commits(commits_value)
    else:
        commits = []
        commits_raw = None

    if precomputed_output is None and branch_name is None:
        raise ValueError(
            f"Linha {row_number}: sem 'branch_name' e sem output pronto para avaliar."
        )

    if precomputed_output is None and not commits:
        raise ValueError(
            f"Linha {row_number}: a execucao real exige a coluna 'commits'."
        )

    test_type = parse_test_type(
        row.get("test_type") or row.get("type"),
        default=default_test_type,
    )

    input_payload = {
        "task": str(row["description"]).strip(),
        "repo_path": str(row["repo_path"]).strip(),
        "branch": str(branch_name).strip() if branch_name is not None else "",
    }

    metadata = {
        "model_name": normalize_scalar(row.get("model_name")) or "gemini-2.5-flash",
        "temperature": parse_temperature(row.get("temperature")),
        "commits": commits_raw,
        "commit_mixed": parse_bool(row.get("commit_mixed")),
        "test_type": test_type.value,
        "project_description": normalize_scalar(row.get("project_description")),
        "github_repo_name": normalize_scalar(row.get("github_repo_name")),
        "ignore_files": parse_ignore_files(row.get("ignore_files")),
        "source_csv_path": str(csv_path),
        "source_row_number": row_number,
        "precomputed_output": precomputed_output,
        "prompt_content": normalize_scalar(row.get("prompt_content")),
        "error_message": normalize_scalar(row.get("error_message")),
        "source_timestamp": normalize_scalar(row.get("timestamp")),
    }

    identity_payload = {
        "input": input_payload,
        "metadata": {
            "model_name": metadata["model_name"],
            "temperature": metadata["temperature"],
            "commits": commits,
            "commit_mixed": metadata["commit_mixed"],
            "test_type": metadata["test_type"],
        },
    }
    item_id = build_dataset_item_id(dataset_name, identity_payload)
    metadata["dataset_item_id"] = item_id

    return {
        "id": item_id,
        "input": input_payload,
        "expected_output": precomputed_output or "",
        "metadata": metadata,
    }


def load_csv_records(csv_path: str | Path) -> list[dict[str, Any]]:
    csv_file = Path(csv_path)
    if not csv_file.exists():
        raise FileNotFoundError(f"CSV nao encontrado: {csv_file}")

    dataframe = pd.read_csv(csv_file)
    records = dataframe.to_dict(orient="records")
    normalized: list[dict[str, Any]] = []
    for record in records:
        normalized.append(canonicalize_csv_row(record))
    return normalized


def ensure_dataset(client: Any, dataset_name: str) -> Any:
    try:
        return client.get_dataset(dataset_name)
    except NotFoundError:
        client.create_dataset(
            name=dataset_name,
            description=(
                "Dataset de avaliacao do GithubDocs para experimentos automatizados "
                "com tracing e judges no Langfuse."
            ),
            metadata={
                "pipeline": "githubdocs",
                "source": "benchmark.dataset_builder",
            },
            input_schema={
                "type": "object",
                "properties": {
                    "task": {"type": "string"},
                    "repo_path": {"type": "string"},
                    "branch": {"type": ["string", "null"]},
                },
                "required": ["task", "repo_path"],
            },
            expected_output_schema={"type": ["string", "null"]},
        )
        return client.get_dataset(dataset_name)


def sync_dataset_from_csv(
    *,
    csv_path: str | Path,
    dataset_name: str = DEFAULT_DATASET_NAME,
    default_test_type: str = DEFAULT_TEST_TYPE,
) -> dict[str, Any]:
    client = require_langfuse_client()
    csv_file = Path(csv_path).resolve()
    rows = load_csv_records(csv_file)
    dataset = ensure_dataset(client, dataset_name)

    existing_ids = {item.id for item in dataset.items}
    upserted = 0
    created = 0
    updated = 0
    skipped = 0

    for row_number, row in enumerate(rows, start=2):
        try:
            payload = _row_to_dataset_payload(
                dataset_name=dataset_name,
                row=row,
                row_number=row_number,
                csv_path=csv_file,
                default_test_type=default_test_type,
            )
        except ValueError as exc:
            missing_required_data = "coluna obrigatoria ausente" in str(exc)
            if missing_required_data:
                skipped += 1
                continue
            raise

        client.create_dataset_item(
            dataset_name=dataset_name,
            id=payload["id"],
            input=payload["input"],
            expected_output=payload["expected_output"],
            metadata=payload["metadata"],
        )
        upserted += 1
        if payload["id"] in existing_ids:
            updated += 1
        else:
            created += 1

    refreshed_dataset = client.get_dataset(dataset_name)
    return {
        "dataset_name": dataset_name,
        "csv_path": str(csv_file),
        "dataset_id": refreshed_dataset.id,
        "dataset_updated_at": refreshed_dataset.updated_at.isoformat(),
        "items_in_dataset": len(refreshed_dataset.items),
        "rows_in_csv": len(rows),
        "upserted": upserted,
        "created": created,
        "updated": updated,
        "skipped": skipped,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Converte um CSV em dataset do Langfuse para o GithubDocs."
    )
    parser.add_argument("csv_path", help="Caminho para o CSV de entrada")
    parser.add_argument(
        "--dataset-name",
        default=DEFAULT_DATASET_NAME,
        help=f"Nome do dataset no Langfuse (default: {DEFAULT_DATASET_NAME})",
    )
    parser.add_argument(
        "--default-test-type",
        default=DEFAULT_TEST_TYPE,
        choices=["readme", "readme_update", "changelog"],
        help=(
            "Tipo de teste padrao quando o CSV nao tiver 'type'/'test_type' "
            f"(default: {DEFAULT_TEST_TYPE})"
        ),
    )
    args = parser.parse_args()

    summary = sync_dataset_from_csv(
        csv_path=args.csv_path,
        dataset_name=args.dataset_name,
        default_test_type=args.default_test_type,
    )

    print(
        "Dataset sincronizado com sucesso: "
        f"{summary['dataset_name']} | "
        f"rows={summary['rows_in_csv']} | "
        f"created={summary['created']} | "
        f"updated={summary['updated']} | "
        f"skipped={summary['skipped']} | "
        f"total={summary['items_in_dataset']}"
    )
    print(f"Dataset version timestamp: {summary['dataset_updated_at']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
