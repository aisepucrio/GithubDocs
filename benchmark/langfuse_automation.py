"""
Single job to sync the dataset, run the experiment, and export results.
"""

from __future__ import annotations

import argparse

from .dataset_builder import sync_dataset_from_csv
from .experiment_runner import run_dataset_experiment
from .export_results import export_dataset_run_results
from .langfuse_utils import (
    DEFAULT_DATASET_NAME,
    DEFAULT_EXPERIMENT_NAME,
    DEFAULT_REQUIRED_SCORES,
    DEFAULT_TEST_TYPE,
    LANGFUSE_OUTPUT_DIR,
    slugify,
)


def run_langfuse_job(
    *,
    csv_path: str,
    dataset_name: str = DEFAULT_DATASET_NAME,
    experiment_name: str = DEFAULT_EXPERIMENT_NAME,
    run_name: str | None = None,
    export_path: str | None = None,
    dataset_version: str | None = None,
    max_concurrency: int = 1,
    default_test_type: str = DEFAULT_TEST_TYPE,
    refine: bool = False,
    required_scores: list[str] | None = None,
    timeout_seconds: int = 900,
    poll_interval_seconds: int = 30,
) -> dict[str, str]:
    dataset_summary = sync_dataset_from_csv(
        csv_path=csv_path,
        dataset_name=dataset_name,
        default_test_type=default_test_type,
    )

    experiment_summary = run_dataset_experiment(
        dataset_name=dataset_name,
        experiment_name=experiment_name,
        run_name=run_name,
        dataset_version=dataset_version,
        max_concurrency=max_concurrency,
        default_test_type=default_test_type,
        refine=refine,
    )

    effective_export_path = export_path
    if effective_export_path is None:
        effective_export_path = str(
            LANGFUSE_OUTPUT_DIR / f"{slugify(experiment_summary['run_name'])}.csv"
        )

    export_summary = export_dataset_run_results(
        dataset_name=dataset_name,
        run_name=experiment_summary["run_name"],
        output_path=effective_export_path,
        required_scores=required_scores or list(DEFAULT_REQUIRED_SCORES),
        wait_for_scores_enabled=True,
        timeout_seconds=timeout_seconds,
        poll_interval_seconds=poll_interval_seconds,
    )

    return {
        "dataset_name": dataset_summary["dataset_name"],
        "dataset_run_name": experiment_summary["run_name"],
        "dataset_run_url": experiment_summary["dataset_run_url"] or "",
        "manifest_path": experiment_summary["manifest_path"],
        "export_path": export_summary["output_path"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Job completo do GithubDocs: CSV -> Dataset Langfuse -> "
            "Experiment -> Scores -> CSV"
        )
    )
    parser.add_argument("csv_path", help="Caminho para o CSV de entrada")
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
    parser.add_argument("--run-name", default=None, help="Nome exato do dataset run")
    parser.add_argument(
        "--export-path",
        default=None,
        help="Caminho do CSV final exportado",
    )
    parser.add_argument(
        "--dataset-version",
        default=None,
        help="Versao ISO 8601 do dataset a usar no experimento (UTC)",
    )
    parser.add_argument(
        "--max-concurrency",
        type=int,
        default=1,
        help="Numero maximo de execucoes paralelas do pipeline (default: 1)",
    )
    parser.add_argument(
        "--default-test-type",
        default=DEFAULT_TEST_TYPE,
        choices=["readme", "readme_update", "changelog"],
        help=(
            "Tipo de teste padrao para linhas sem 'type'/'test_type' "
            f"(default: {DEFAULT_TEST_TYPE})"
        ),
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
        "--timeout-seconds",
        type=int,
        default=900,
        help="Tempo maximo de espera pelos scores do UI evaluator (default: 900)",
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=int,
        default=30,
        help="Intervalo de polling para scores (default: 30)",
    )
    parser.add_argument(
        "--refine",
        action="store_true",
        help="Ativa refinamento de arquivos grandes antes de enviar ao modelo",
    )
    args = parser.parse_args()

    result = run_langfuse_job(
        csv_path=args.csv_path,
        dataset_name=args.dataset_name,
        experiment_name=args.experiment_name,
        run_name=args.run_name,
        export_path=args.export_path,
        dataset_version=args.dataset_version,
        max_concurrency=args.max_concurrency,
        default_test_type=args.default_test_type,
        required_scores=args.required_scores or list(DEFAULT_REQUIRED_SCORES),
        timeout_seconds=args.timeout_seconds,
        poll_interval_seconds=args.poll_interval_seconds,
        refine=args.refine,
    )

    print(f"Job concluido para o dataset: {result['dataset_name']}")
    print(f"Dataset run: {result['dataset_run_name']}")
    if result["dataset_run_url"]:
        print(f"Langfuse: {result['dataset_run_url']}")
    print(f"Manifesto: {result['manifest_path']}")
    print(f"CSV final: {result['export_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
