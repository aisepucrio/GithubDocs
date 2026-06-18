import argparse
import logging
import os
import sys
import time
from contextlib import nullcontext

from dotenv import load_dotenv

from src.facade import start
from src.load_configuration import load_config
from src.load_configuration.conf_structures import CliParams
from src.log import CustomLogger


def _configure_run_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("config_path", help="Path to the configuration file.")
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock agent for testing.",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging.")
    parser.add_argument(
        "--refine",
        action="store_true",
        help=(
            "Ativa refinamento de arquivos grandes via load_summarize_chain "
            "antes de enviar ao modelo."
        ),
    )
    parser.add_argument(
        "--map-reduce",
        action="store_true",
        help=(
            "Ativa map-reduce: sumariza cada arquivo via batch e reduz com o "
            "prompt original."
        ),
    )
    parser.add_argument(
        "--tool-calling",
        action="store_true",
        help=(
            "Substitui o prompt-com-dicionario por um prompt minimo + tool "
            "calling. O LLM puxa dados do repo sob demanda via tools do "
            "RepoInfoExtractor."
        ),
    )


def _configure_eval_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("csv_path", help="Caminho para o CSV de entrada")
    parser.add_argument(
        "--dataset-name",
        default="gh-docs-eval",
        help="Nome do dataset no Langfuse (default: gh-docs-eval)",
    )
    parser.add_argument(
        "--experiment-name",
        default="gh-docs-experiment",
        help="Nome logico do experimento (default: gh-docs-experiment)",
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
        default="readme_update",
        choices=["readme", "readme_update", "changelog"],
        help="Tipo de teste padrao para linhas sem 'type'/'test_type'",
    )
    parser.add_argument(
        "--required-score",
        dest="required_scores",
        action="append",
        default=None,
        help="Score esperado no export. Pode ser repetido.",
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


def _run_manual_case(args: argparse.Namespace) -> int:
    from src.llm_agent.langfuse_integration import (
        build_run_metadata,
        build_run_tags,
        clear_current_trace_id,
        get_langfuse_client,
        set_current_trace_id,
    )

    logger = CustomLogger()
    if args.debug:
        logger.log_level = logging.DEBUG

    logger.info("Loading configuration...")
    config = load_config(args.config_path)

    if args.mock:
        logger.warning("Using mock agent.")
        for step in config.orchestration_steps:
            step.model_name = "mock"

    if args.debug:
        logger.debug("Configuration loaded:")
        logger.debug(f"Target Info: {config.target_info}")
        logger.debug(f"Output Info: {config.output_info}")
        for step in config.orchestration_steps:
            logger.debug(f"Orchestration Step: {step}")

    config.cli_params = CliParams(
        refine=args.refine,
        map_reduce=args.map_reduce,
        tool_calling=args.tool_calling,
    )

    lf_client = get_langfuse_client()
    trace_id = None
    span = None
    if lf_client:
        from langfuse import Langfuse, propagate_attributes

        model_names = [step.model_name for step in config.orchestration_steps]
        temperatures = [step.temperature for step in config.orchestration_steps]
        trace_metadata = build_run_metadata(
            repo_path=config.target_info.repo_path,
            branch_name=config.target_info.branch_name,
            commit_list=config.target_info.commit_list,
            config_file=args.config_path,
            model_names=model_names,
            temperatures=temperatures,
        )
        trace_input = {
            "config_file": args.config_path,
            "repo_path": config.target_info.repo_path,
            "branch_name": config.target_info.branch_name,
            "commit_count": len(config.target_info.commit_list or []),
            "steps": [
                {
                    "step": step.step,
                    "model_name": step.model_name,
                    "prompt_file": step.prompt_file,
                    "tools": step.tools,
                }
                for step in config.orchestration_steps
            ],
        }
        trace_id = Langfuse.create_trace_id()
        span = lf_client.start_observation(
            trace_context={"trace_id": trace_id},
            name="githubdocs-manual-run",
            as_type="chain",
            input=trace_input,
            metadata=trace_metadata,
        )
        set_current_trace_id(trace_id)
        trace_attributes_context = propagate_attributes(
            trace_name="githubdocs-manual-run",
            metadata=trace_metadata,
            tags=build_run_tags(model_names),
        )
    else:
        trace_attributes_context = nullcontext()

    start_time = time.monotonic()
    success = False
    error_message = None
    try:
        logger.info("Starting documentation generation...")
        with trace_attributes_context:
            start(config)
        success = True
    except Exception as exc:
        error_message = str(exc)
        raise
    finally:
        elapsed = round(time.monotonic() - start_time, 2)
        if trace_id and span:
            clear_current_trace_id()
            output_path = os.path.join(
                config.output_info.result_path,
                config.output_info.result_file_name,
            )
            output_content = ""
            try:
                with open(output_path, encoding="utf-8") as f:
                    output_content = f.read()
            except OSError:
                pass
            output = {}
            if output_content:
                output["content"] = output_content
            if error_message:
                output["error"] = error_message
            span.update(
                output=output or None,
                level="DEFAULT" if success else "ERROR",
                status_message=error_message,
                metadata={
                    **trace_metadata,
                    "success": str(success),
                    "execution_time_seconds": str(elapsed),
                },
            )
            span.end()
            lf_client.create_score(
                trace_id=trace_id,
                name="sucesso",
                value=1.0 if success else 0.0,
                data_type="BOOLEAN",
            )
            lf_client.create_score(
                trace_id=trace_id,
                name="tempo",
                value=elapsed,
                data_type="NUMERIC",
            )
            from benchmark.langfuse_annotation import enqueue_traces_for_annotation

            enqueue_traces_for_annotation(lf_client, [trace_id])
            lf_client.flush()

    return 0


def _run_langfuse_eval(args: argparse.Namespace) -> int:
    from benchmark.langfuse_automation import run_langfuse_job

    result = run_langfuse_job(
        csv_path=args.csv_path,
        dataset_name=args.dataset_name,
        experiment_name=args.experiment_name,
        run_name=args.run_name,
        export_path=args.export_path,
        dataset_version=args.dataset_version,
        max_concurrency=args.max_concurrency,
        default_test_type=args.default_test_type,
        refine=args.refine,
        required_scores=args.required_scores,
        timeout_seconds=args.timeout_seconds,
        poll_interval_seconds=args.poll_interval_seconds,
    )

    print(f"Job concluido para o dataset: {result['dataset_name']}")
    print(f"Dataset run: {result['dataset_run_name']}")
    if result["dataset_run_url"]:
        print(f"Langfuse: {result['dataset_run_url']}")
    print(f"Manifesto: {result['manifest_path']}")
    print(f"CSV final: {result['export_path']}")
    if result.get("annotation_queue_id"):
        print(
            "Annotation queue: "
            f"{result['annotation_queue_id']} | "
            f"queued={result['annotation_queued']} | "
            f"skipped={result['annotation_skipped']} | "
            f"failed={result['annotation_failed']}"
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="GithubDocs CLI")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser(
        "run",
        help="Executa um caso manual usando um arquivo TOML de configuracao",
    )
    _configure_run_parser(run_parser)

    eval_parser = subparsers.add_parser(
        "eval",
        help="Executa o fluxo completo de avaliacao com Langfuse",
    )
    _configure_eval_parser(eval_parser)

    raw_argv = list(sys.argv[1:] if argv is None else argv)

    # Compatibilidade com o uso antigo:
    # python main.py conf/config.toml
    if raw_argv and raw_argv[0] not in {"run", "eval", "-h", "--help"}:
        raw_argv = ["run", *raw_argv]

    args = parser.parse_args(raw_argv)

    if args.command == "eval":
        return _run_langfuse_eval(args)

    return _run_manual_case(args)


if __name__ == "__main__":
    load_dotenv()
    raise SystemExit(main())
