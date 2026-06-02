"""
Executa experimentos no Langfuse usando o pipeline real do GithubDocs.
"""

from __future__ import annotations

import argparse
import json
from typing import Any

from src.facade import start

from .langfuse_utils import (
    DEFAULT_DATASET_NAME,
    DEFAULT_EXPERIMENT_NAME,
    DEFAULT_TEST_TYPE,
    LANGFUSE_OUTPUT_DIR,
    build_pipeline_config,
    now_utc_iso,
    parse_dataset_version,
    parse_test_type,
    require_langfuse_client,
    serialize_for_csv,
    slugify,
)


def run_github_docs_pipeline(
    input_payload: dict[str, Any],
    metadata: dict[str, Any],
    *,
    run_name: str,
    refine: bool = False,
) -> str:
    precomputed_output = metadata.get("precomputed_output")
    if precomputed_output is not None:
        return str(precomputed_output)

    commits_value = metadata.get("commits")
    if commits_value is None:
        raise ValueError("Metadata do dataset item nao contem 'commits'.")

    commits = [part.strip() for part in str(commits_value).split(",") if part.strip()]
    if not commits:
        raise ValueError("Metadata do dataset item nao contem commits validos.")

    item_id = metadata.get("dataset_item_id") or slugify(
        f"{input_payload['repo_path']}-{input_payload['branch']}-{input_payload['task']}"
    )
    output_file_name = f"{slugify(run_name)}-{item_id}.md"
    test_type = parse_test_type(metadata.get("test_type"), default=DEFAULT_TEST_TYPE)

    config = build_pipeline_config(
        task=str(input_payload["task"]),
        repo_path=str(input_payload["repo_path"]),
        branch_name=str(input_payload["branch"]),
        commits=commits,
        model_name=str(metadata.get("model_name") or "gemini-2.5-flash"),
        temperature=float(metadata.get("temperature", 0.2)),
        test_type=test_type,
        output_file_name=output_file_name,
        project_description=metadata.get("project_description"),
    )

    config.cli_params.refine = refine
    start(config)
    output_path = LANGFUSE_OUTPUT_DIR / output_file_name
    return output_path.read_text(encoding="utf-8") if output_path.exists() else ""


def run_dataset_experiment(
    *,
    dataset_name: str = DEFAULT_DATASET_NAME,
    experiment_name: str = DEFAULT_EXPERIMENT_NAME,
    run_name: str | None = None,
    dataset_version: str | None = None,
    max_concurrency: int = 1,
    default_test_type: str = DEFAULT_TEST_TYPE,
    refine: bool = False,
    limit: int | None = None,
) -> dict[str, Any]:
    client = require_langfuse_client()
    parsed_version = parse_dataset_version(dataset_version)
    dataset = client.get_dataset(dataset_name, version=parsed_version)
    items = dataset.items[:limit] if limit else dataset.items

    if not items:
        raise ValueError(f"Dataset '{dataset_name}' nao contem items para executar.")

    effective_run_name = run_name or f"{experiment_name}-{slugify(now_utc_iso())}"

    def task(*, item: Any, **_: dict[str, Any]) -> str:
        item_input = item.input if hasattr(item, "input") else item["input"]
        item_metadata = item.metadata if hasattr(item, "metadata") else item["metadata"]
        item_metadata = dict(item_metadata or {})
        item_metadata.setdefault("test_type", default_test_type)
        return run_github_docs_pipeline(
            item_input,
            item_metadata,
            run_name=effective_run_name,
            refine=refine,
        )

    result = client.run_experiment(
        name=experiment_name,
        run_name=effective_run_name,
        description=(
            "Experimento automatizado do GithubDocs com pipeline real de geracao."
        ),
        data=items,
        task=task,
        evaluators=[],
        max_concurrency=max_concurrency,
        metadata={
            "pipeline": "githubdocs",
            "dataset_name": dataset_name,
            "default_test_type": default_test_type,
        },
        _dataset_version=parsed_version or dataset.version,
    )
    client.flush()

    manifest = {
        "dataset_name": dataset_name,
        "experiment_name": experiment_name,
        "run_name": result.run_name,
        "dataset_run_id": result.dataset_run_id,
        "dataset_run_url": result.dataset_run_url,
        "dataset_version": parsed_version.isoformat() if parsed_version else None,
        "item_count": len(result.item_results),
        "trace_ids": [item_result.trace_id for item_result in result.item_results],
    }

    manifest_path = LANGFUSE_OUTPUT_DIR / f"{slugify(result.run_name)}.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {
        **manifest,
        "manifest_path": str(manifest_path),
        "summary": result.format(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Executa um experimento do GithubDocs em um dataset do Langfuse."
    )
    parser.add_argument(
        "--dataset-name",
        default=DEFAULT_DATASET_NAME,
        help=f"Nome do dataset no Langfuse (default: {DEFAULT_DATASET_NAME})",
    )
    parser.add_argument(
        "--experiment-name",
        default=DEFAULT_EXPERIMENT_NAME,
        help=f"Nome logico do experimento (default: {DEFAULT_EXPERIMENT_NAME})",
    )
    parser.add_argument(
        "--run-name",
        default=None,
        help="Nome exato do dataset run no Langfuse",
    )
    parser.add_argument(
        "--dataset-version",
        default=None,
        help="Versao ISO 8601 do dataset a usar (UTC). Ex.: 2026-03-25T12:00:00Z",
    )
    parser.add_argument(
        "--max-concurrency",
        type=int,
        default=1,
        help="Numero maximo de items processados em paralelo (default: 1)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limita a quantidade de items executados neste run",
    )
    parser.add_argument(
        "--default-test-type",
        default=DEFAULT_TEST_TYPE,
        choices=["readme", "readme_update", "changelog"],
        help=(
            "Tipo de teste padrao quando o item nao tiver metadata.test_type "
            f"(default: {DEFAULT_TEST_TYPE})"
        ),
    )
    parser.add_argument(
        "--refine",
        action="store_true",
        help="Ativa refinamento de arquivos grandes antes do envio ao modelo",
    )
    args = parser.parse_args()

    result = run_dataset_experiment(
        dataset_name=args.dataset_name,
        experiment_name=args.experiment_name,
        run_name=args.run_name,
        dataset_version=args.dataset_version,
        max_concurrency=args.max_concurrency,
        default_test_type=args.default_test_type,
        refine=args.refine,
        limit=args.limit,
    )

    print(result["summary"])
    print(f"\nDataset run: {result['run_name']}")
    print(f"Manifesto salvo em: {result['manifest_path']}")
    print(f"Dataset Run URL: {serialize_for_csv(result['dataset_run_url'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
