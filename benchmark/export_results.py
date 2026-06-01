"""
Exporta resultados do Langfuse para CSV estruturado.
"""

from __future__ import annotations

import argparse
import time
from typing import Any

import pandas as pd

from .langfuse_utils import (
    DEFAULT_DATASET_NAME,
    DEFAULT_REQUIRED_SCORES,
    ensure_absolute_output_path,
    get_langfuse_base_url,
    iter_pages,
    require_langfuse_client,
    score_value_to_python,
    serialize_for_csv,
)


def _fetch_all_scores(client: Any, dataset_run_id: str) -> list[Any]:
    return list(
        iter_pages(
            lambda page: client.api.scores.get_many(
                dataset_run_id=dataset_run_id,
                page=page,
                limit=100,
            )
        )
    )


def wait_for_scores(
    *,
    dataset_name: str,
    run_name: str,
    required_scores: list[str],
    timeout_seconds: int,
    poll_interval_seconds: int,
) -> dict[str, Any]:
    client = require_langfuse_client()
    dataset_run = client.get_dataset_run(dataset_name=dataset_name, run_name=run_name)

    if not required_scores:
        return {
            "dataset_run": dataset_run,
            "scores": _fetch_all_scores(client, dataset_run.id),
            "complete": True,
        }

    expected_pairs = {
        (item.trace_id, score_name)
        for item in dataset_run.dataset_run_items
        for score_name in required_scores
    }

    deadline = time.time() + timeout_seconds
    scores: list[Any] = []
    complete = False

    while time.time() <= deadline:
        scores = _fetch_all_scores(client, dataset_run.id)
        existing_pairs = {
            (score.trace_id, score.name)
            for score in scores
            if score.name in required_scores
        }
        if expected_pairs.issubset(existing_pairs):
            complete = True
            break

        time.sleep(poll_interval_seconds)

    return {
        "dataset_run": dataset_run,
        "scores": scores,
        "complete": complete,
    }


def export_dataset_run_results(
    *,
    dataset_name: str,
    run_name: str,
    output_path: str,
    required_scores: list[str] | None = None,
    wait_for_scores_enabled: bool = True,
    timeout_seconds: int = 900,
    poll_interval_seconds: int = 30,
) -> dict[str, Any]:
    client = require_langfuse_client()
    score_names = list(required_scores or DEFAULT_REQUIRED_SCORES)

    if wait_for_scores_enabled:
        waited = wait_for_scores(
            dataset_name=dataset_name,
            run_name=run_name,
            required_scores=score_names,
            timeout_seconds=timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )
        dataset_run = waited["dataset_run"]
        scores = waited["scores"]
        scores_complete = waited["complete"]
    else:
        dataset_run = client.get_dataset_run(
            dataset_name=dataset_name, run_name=run_name
        )
        scores = _fetch_all_scores(client, dataset_run.id)
        scores_complete = False

    scores_by_trace: dict[str, dict[str, Any]] = {}
    discovered_score_names = set(score_names)
    for score in sorted(scores, key=lambda current: current.created_at):
        trace_scores = scores_by_trace.setdefault(score.trace_id, {})
        trace_scores[score.name] = score_value_to_python(score)
        discovered_score_names.add(score.name)

    rows: list[dict[str, Any]] = []
    for run_item in dataset_run.dataset_run_items:
        trace = client.api.trace.get(run_item.trace_id)

        trace_input = trace.input if isinstance(trace.input, dict) else {}
        trace_metadata = trace.metadata if isinstance(trace.metadata, dict) else {}
        row = {
            "model_name": trace_metadata.get("model_name"),
            "temperature": trace_metadata.get("temperature"),
            "repo_path": trace_input.get("repo_path"),
            "branch_name": trace_input.get("branch"),
            "commits": trace_metadata.get("commits"),
            "commit_mixed": trace_metadata.get("commit_mixed"),
            "test_type": trace_metadata.get("test_type"),
            "description": trace_input.get("task"),
            "output": serialize_for_csv(trace.output),
            "trace_id": trace.id,
            "trace_url": f"{get_langfuse_base_url()}{trace.html_path}",
            "dataset_name": dataset_run.dataset_name,
            "dataset_run_name": dataset_run.name,
            "dataset_run_id": dataset_run.id,
            "timestamp": trace.timestamp.isoformat(),
        }
        row.update(scores_by_trace.get(trace.id, {}))
        rows.append(row)

    ordered_scores = [name for name in score_names if name in discovered_score_names]
    ordered_scores.extend(
        sorted(name for name in discovered_score_names if name not in ordered_scores)
    )

    ordered_columns = [
        "model_name",
        "temperature",
        "repo_path",
        "branch_name",
        "commits",
        "commit_mixed",
        "test_type",
        "description",
        *ordered_scores,
        "output",
        "trace_id",
        "trace_url",
        "dataset_name",
        "dataset_run_name",
        "dataset_run_id",
        "timestamp",
    ]

    dataframe = pd.DataFrame(rows)
    if dataframe.empty:
        dataframe = pd.DataFrame(columns=ordered_columns)
    else:
        for column in ordered_columns:
            if column not in dataframe.columns:
                dataframe[column] = None
        dataframe = dataframe[ordered_columns]

    csv_path = ensure_absolute_output_path(output_path)
    dataframe.to_csv(csv_path, index=False)

    return {
        "dataset_name": dataset_name,
        "run_name": run_name,
        "dataset_run_id": dataset_run.id,
        "output_path": str(csv_path),
        "row_count": len(dataframe),
        "scores_complete": scores_complete,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Exporta resultados estruturados do Langfuse para CSV."
    )
    parser.add_argument(
        "--dataset-name",
        default=DEFAULT_DATASET_NAME,
        help=f"Nome do dataset no Langfuse (default: {DEFAULT_DATASET_NAME})",
    )
    parser.add_argument(
        "--run-name",
        required=True,
        help="Nome exato do dataset run no Langfuse",
    )
    parser.add_argument(
        "--output-path",
        required=True,
        help="Caminho do CSV de saida",
    )
    parser.add_argument(
        "--required-score",
        dest="required_scores",
        action="append",
        default=None,
        help=(
            "Score esperado no export. Pode ser repetido. "
            "Default: doc_quality, hallucination, consistency"
        ),
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Nao espera a chegada dos scores do evaluator antes de exportar",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=900,
        help="Tempo maximo de espera pelos scores (default: 900)",
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=int,
        default=30,
        help="Intervalo entre verificacoes de score (default: 30)",
    )
    args = parser.parse_args()

    result = export_dataset_run_results(
        dataset_name=args.dataset_name,
        run_name=args.run_name,
        output_path=args.output_path,
        required_scores=args.required_scores or list(DEFAULT_REQUIRED_SCORES),
        wait_for_scores_enabled=not args.no_wait,
        timeout_seconds=args.timeout_seconds,
        poll_interval_seconds=args.poll_interval_seconds,
    )

    print(
        f"Export concluido: {result['row_count']} linha(s) -> {result['output_path']}"
    )
    if not result["scores_complete"] and not args.no_wait:
        print(
            "Aviso: o timeout expirou antes de todos os scores esperados "
            "chegarem ao Langfuse."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
