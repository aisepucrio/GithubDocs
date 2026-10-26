"""
Exporta resultados do Langfuse para CSV estruturado.
"""

from __future__ import annotations

import argparse
import json
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


def _iso(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


def _observation_row(observation: Any, trace_id: str) -> dict[str, Any]:
    """Keep the provider's detailed usage alongside Langfuse's normalized usage."""
    usage = getattr(observation, "usage", None)
    return {
        "trace_id": trace_id,
        "observation_id": getattr(observation, "id", None),
        "type": getattr(observation, "type", None),
        "model": getattr(observation, "model", None),
        "start_time": _iso(getattr(observation, "start_time", None)),
        "end_time": _iso(getattr(observation, "end_time", None)),
        "usage_unit": getattr(usage, "unit", None),
        "input": getattr(usage, "input", None),
        "output": getattr(usage, "output", None),
        "total": getattr(usage, "total", None),
        "usage_details": getattr(observation, "usage_details", None),
        "cost_details": getattr(observation, "cost_details", None),
        "calculated_total_cost": getattr(observation, "calculated_total_cost", None),
    }


def _token_totals(observations: list[dict[str, Any]]) -> dict[str, Any]:
    # Spans may repeat their children's usage: only count GENERATION observations.
    generations = [row for row in observations if row["type"] == "GENERATION"]
    totals = {}
    for key in ("input", "output", "total"):
        complete = bool(generations) and all(
            row["usage_unit"] in (None, "TOKENS", "tokens")
            and isinstance(row[key], (int, float))
            for row in generations
        )
        totals[f"{key}_tokens"] = (
            sum(row[key] for row in generations) if complete else None
        )
    return totals


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

    # The wide CSV remains a latest-score view for existing consumers. The sidecar
    # below is the lossless source for individual-rater analysis and score history.
    score_columns = [
        "score_id",
        "trace_id",
        "observation_id",
        "name",
        "value",
        "data_type",
        "source",
        "author_user_id",
        "comment",
        "created_at",
        "updated_at",
        "dataset_run_id",
    ]
    score_rows = [
        {
            "score_id": getattr(score, "id", None),
            "trace_id": score.trace_id,
            "observation_id": getattr(score, "observation_id", None),
            "name": score.name,
            "value": score_value_to_python(score),
            "data_type": getattr(score, "data_type", None),
            "source": getattr(score, "source", None),
            "author_user_id": getattr(score, "author_user_id", None),
            "comment": getattr(score, "comment", None),
            "created_at": _iso(getattr(score, "created_at", None)),
            "updated_at": _iso(getattr(score, "updated_at", None)),
            "dataset_run_id": dataset_run.id,
        }
        for score in scores
    ]
    observation_rows: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    seen_traces: set[str] = set()
    for run_item in dataset_run.dataset_run_items:
        trace = client.api.trace.get(run_item.trace_id)

        trace_input = trace.input if isinstance(trace.input, dict) else {}
        trace_metadata = trace.metadata if isinstance(trace.metadata, dict) else {}
        observations = [
            _observation_row(observation, trace.id)
            for observation in (getattr(trace, "observations", None) or [])
        ]
        if trace.id not in seen_traces:
            observation_rows.extend(observations)
            seen_traces.add(trace.id)
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
            "latency_seconds": getattr(trace, "latency", None),
            "total_cost": getattr(trace, "total_cost", None),
            "execution_time_seconds": trace_metadata.get("execution_time_seconds"),
            "success": trace_metadata.get("success"),
            "error_message": trace_metadata.get("error_message"),
            **_token_totals(observations),
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
        "latency_seconds",
        "total_cost",
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "execution_time_seconds",
        "success",
        "error_message",
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
    scores_path = csv_path.with_suffix(".scores.csv")
    observations_path = csv_path.with_suffix(".observations.jsonl")
    pd.DataFrame(score_rows, columns=score_columns).to_csv(scores_path, index=False)
    with observations_path.open("w", encoding="utf-8") as handle:
        for row in observation_rows:
            handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")

    return {
        "dataset_name": dataset_name,
        "run_name": run_name,
        "dataset_run_id": dataset_run.id,
        "output_path": str(csv_path),
        "row_count": len(dataframe),
        "scores_complete": scores_complete,
        "scores_path": str(scores_path),
        "score_count": len(score_rows),
        "observations_path": str(observations_path),
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
