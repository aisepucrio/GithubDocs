"""
Runner de benchmark - executa os testes e coleta métricas.
"""

import argparse
import shlex
import signal
import threading
import time
import traceback
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import tomllib
import sys
import os

# Timeout de parede padrao (segundos) para UMA tentativa de execucao de uma
# config. Cobre toda a chain (extracao + todos os steps) de uma tentativa.
DEFAULT_STEP_TIMEOUT_SECONDS = 200

# Numero padrao de tentativas por config antes de marcar como falha e seguir.
# Uma config que trava (ex.: Ollama sem responder) ou que falha por erro
# transitorio costuma passar numa nova tentativa (agente e conexao sao
# recriados do zero a cada start()).
DEFAULT_MAX_ATTEMPTS = 3


class StepTimeoutError(TimeoutError):
    """Disparado quando a execucao de uma config excede o timeout de parede."""


@contextmanager
def step_timeout(seconds: Optional[int]):
    """Aborta o bloco com StepTimeoutError se ele exceder `seconds`.

    Usa SIGALRM (Unix, somente main thread): interrompe inclusive chamadas de
    rede bloqueadas (ex.: Ollama travado sem responder), que e justamente o caso
    em que o benchmark congelava o batch inteiro. Se SIGALRM nao estiver
    disponivel ou nao estivermos na main thread, vira no-op (sem timeout).
    """
    if (
        not seconds
        or seconds <= 0
        or not hasattr(signal, "SIGALRM")
        or threading.current_thread() is not threading.main_thread()
    ):
        yield
        return

    def _handler(signum, frame):
        raise StepTimeoutError(
            f"Config execution exceeded the {seconds}s wall-clock timeout"
        )

    previous_handler = signal.signal(signal.SIGALRM, _handler)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)

# Adiciona o diretório pai ao path para importar GithubDocs
BENCHMARK_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(BENCHMARK_DIR)  # githubdocs/
GITHUBDOCS_DIR = os.path.join(PARENT_DIR, "GithubDocs")  # for internal src imports
sys.path.insert(0, PARENT_DIR)
sys.path.insert(0, GITHUBDOCS_DIR)

from src.facade import (
    start,
    render_prompt,
    TOOL_CALLING_TEMPLATE_PATH,
    _resolve_tool_calling_prompt,
)
from src.load_configuration.conf_structures import BaseAppConfig, CliParams
from src.repo_info_extraction import RepoInfoExtractor

from .test_configs import ConfigMetadata
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .langfuse_exporter import LangfuseExporter


def _build_cli_params_parser() -> argparse.ArgumentParser:
    """Espelha as flags suportadas em main.py para parsing da coluna `parameters`."""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--mock", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--refine", action="store_true")
    parser.add_argument("--map-reduce", action="store_true")
    parser.add_argument("--tool-calling", action="store_true")
    return parser


def parse_parameters_string(parameters: str) -> tuple[CliParams, bool]:
    """
    Parseia a string de parâmetros (ex: "--map-reduce --refine") nos mesmos
    flags aceitos por main.py. Retorna (CliParams, mock).
    Argumentos desconhecidos são ignorados (com aviso via stderr).
    """
    if not parameters or not parameters.strip():
        return CliParams(), False

    tokens = shlex.split(parameters)
    parser = _build_cli_params_parser()
    args, unknown = parser.parse_known_args(tokens)
    if unknown:
        print(f"Aviso: parâmetros desconhecidos ignorados: {unknown}", file=sys.stderr)

    cli_params = CliParams(
        refine=args.refine,
        map_reduce=args.map_reduce,
        tool_calling=args.tool_calling,
    )
    return cli_params, args.mock


@dataclass
class BenchmarkResult:
    """Resultado de um único benchmark."""
    config_index: int
    config_name: str
    success: bool
    execution_time_seconds: float
    output_file: Optional[str] = None
    output_content: Optional[str] = None
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    model_name: Optional[str] = None
    temperature: Optional[float] = None
    repo_path: Optional[str] = None
    description: str = ""
    commit_mixed: bool = False
    prompt_content: Optional[str] = None
    test_type: Optional[str] = None
    parameters: str = ""

    def to_dict(self) -> dict:
        """Converte para dicionário para exportação."""
        return {
            "config_index": self.config_index + 1,  # 1-based para usuário
            "description": self.description,
            "commit_mixed": "Sim" if self.commit_mixed else "Não",
            "success": "Sim" if self.success else "Não",
            "execution_time_seconds": round(self.execution_time_seconds, 2),
            "output_file": self.output_file or "",
            "output_content": self.output_content or "",
            "error_message": self.error_message or "",
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "model_name": self.model_name or "",
            "temperature": self.temperature if self.temperature is not None else "",
            "repo_path": self.repo_path or "",
            "prompt_content": self.prompt_content or "",
            "test_type": self.test_type or "",
            "parameters": self.parameters or "",
        }


class BenchmarkRunner:
    """Executa benchmarks de configs."""

    def __init__(
        self,
        configs: list[str],
        names: list[str],
        metadata: Optional[list[ConfigMetadata]] = None,
        verbose: bool = True,
        refine: bool = False,
        langfuse_exporter: Optional["LangfuseExporter"] = None,
        timeout_seconds: Optional[int] = DEFAULT_STEP_TIMEOUT_SECONDS,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    ):
        """
        Args:
            configs: Lista de strings TOML com as configurações
            names: Lista de nomes descritivos para cada config
            metadata: Lista de metadados (description, commit_mixed) para cada config
            verbose: Se True, imprime logs detalhados
            refine: Se True, ativa refinamento de arquivos grandes via load_summarize_chain
            timeout_seconds: Timeout de parede por TENTATIVA de execucao. Se uma
                tentativa exceder, ela e abortada e (se restarem tentativas) a
                config e re-executada. <=0 ou None desativa o timeout.
            max_attempts: Numero de tentativas por config antes de marcar como
                falha e seguir para a proxima. <=1 desativa o retry.
        """
        self.configs = configs
        self.names = names
        self.metadata = metadata or [ConfigMetadata() for _ in configs]
        self.verbose = verbose
        self.refine = refine
        self.timeout_seconds = timeout_seconds
        self.max_attempts = max(1, max_attempts)
        self.results: list[BenchmarkResult] = []
        self.langfuse_exporter = langfuse_exporter
        self._run_name: Optional[str] = None

    def _get_config_name(self, index: int) -> str:
        """Retorna o nome da config pelo índice."""
        if index < len(self.names) and self.names[index]:
            return self.names[index]
        return f"Config {index + 1}"

    def _get_metadata(self, index: int) -> ConfigMetadata:
        """Retorna os metadados da config pelo índice."""
        if index < len(self.metadata):
            return self.metadata[index]
        return ConfigMetadata()

    def _log(self, message: str):
        """Log condicional."""
        if self.verbose:
            print(message)

    def _parse_config_string(self, config_str: str) -> BaseAppConfig:
        """
        Parseia uma string TOML e retorna um BaseAppConfig.
        Reutiliza a lógica do load_config mas com string em vez de arquivo.
        """
        data = tomllib.loads(config_str)

        target_info = data.get("target_information", {})
        agents = data.get("agents", {})

        output_list = agents.get("output", [])
        output_info = output_list[0] if output_list else {}

        orchestration_list = agents.get("orchestration", [])

        from src.load_configuration.conf_structures import (
            TargetInfo,
            OutputInfo,
            OrchestrationStep,
            BaseAppConfig,
        )

        config = BaseAppConfig(
            target_info=TargetInfo(**target_info),
            output_info=OutputInfo(**output_info),
            orchestration_steps=[OrchestrationStep(**step) for step in orchestration_list],
        )

        return config

    def run_single(self, config_index: int) -> BenchmarkResult:
        """
        Executa um único benchmark.

        Args:
            config_index: Índice da config (0-based)

        Returns:
            BenchmarkResult com os resultados
        """
        config_name = self._get_config_name(config_index)
        config_str = self.configs[config_index]
        meta = self._get_metadata(config_index)

        self._log(f"\n{'='*60}")
        self._log(f"Executando: {config_name} (índice {config_index + 1})")
        self._log(f"{'='*60}")

        start_time = time.time()
        result = BenchmarkResult(
            config_index=config_index,
            config_name=config_name,
            success=False,
            execution_time_seconds=0,
            description=meta.description,
            commit_mixed=meta.commit_mixed,
            parameters=meta.parameters,
        )

        try:
            config = self._parse_config_string(config_str)

            # Extrai metadados
            result.repo_path = config.target_info.repo_path
            if config.orchestration_steps:
                result.model_name = config.orchestration_steps[0].model_name
                result.temperature = config.orchestration_steps[0].temperature
                # Extrai tipo do teste do nome do arquivo de prompt (e.g., "readme_update.jinja" -> "readme_update")
                prompt_file = config.orchestration_steps[0].prompt_file
                if prompt_file:
                    result.test_type = os.path.splitext(prompt_file)[0]

            result.output_file = os.path.join(
                config.output_info.result_path,
                config.output_info.result_file_name
            )

            self._log(f"Modelo: {result.model_name}")
            self._log(f"Temperatura: {result.temperature}")
            self._log(f"Repo: {result.repo_path}")
            self._log(f"Output: {result.output_file}")
            self._log("-" * 40)

            # Aplica parâmetros por linha (coluna `parameters`), espelhando main.py.
            # A flag global --refine continua valendo como fallback.
            # Tem que vir ANTES da captura do prompt: --tool-calling troca o template.
            row_cli_params, row_mock = parse_parameters_string(meta.parameters)
            if self.refine:
                row_cli_params.refine = True
            config.cli_params = row_cli_params

            if row_mock:
                self._log("Mock mode habilitado via parameters")
                for step in config.orchestration_steps:
                    step.model_name = "mock"

            if meta.parameters:
                self._log(f"Parameters: {meta.parameters}")

            # Captura o prompt renderizado antes de executar.
            # Em modo --tool-calling, o facade usa um template diferente
            # (prompt/tool-calling/) com template_vars enxutos e sem repo_info.
            try:
                if config.orchestration_steps:
                    step = config.orchestration_steps[0]
                    if row_cli_params.tool_calling:
                        prompt_file_resolved = _resolve_tool_calling_prompt(step.prompt_file)
                        template_vars = {"prompt_variables": step.prompt_variables}
                        result.prompt_content = render_prompt(
                            TOOL_CALLING_TEMPLATE_PATH,
                            prompt_file_resolved,
                            template_vars,
                            config.target_info.repo_path,
                        )
                    else:
                        extractor = RepoInfoExtractor(
                            repository_path=config.target_info.repo_path,
                            commit_list=config.target_info.commit_list,
                            target_branch=config.target_info.branch_name,
                            ignored_files=config.target_info.ignore_files,
                        )
                        repo_info = extractor.extract_repo_info()
                        template_vars = step.prompt_variables.copy()
                        template_vars['repo_info'] = repo_info
                        result.prompt_content = render_prompt(
                            step.template_path,
                            step.prompt_file,
                            template_vars,
                            repo_info["repo_path"],
                        )
            except Exception as prompt_err:
                self._log(f"Aviso: Não foi possível capturar o prompt: {prompt_err}")

            # Inicia trace Langfuse antes de executar (vincula spans LLM ao trace pai)
            langfuse_attributes_context = nullcontext()
            if self.langfuse_exporter and self._run_name:
                trace_metadata = {
                    "config_index": config_index + 1,
                    "description": result.description,
                    "commit_mixed": result.commit_mixed,
                    "model_name": result.model_name or "",
                    "temperature": result.temperature,
                    "repo_path": result.repo_path or "",
                    "test_type": result.test_type or "",
                }
                self.langfuse_exporter.start_trace(
                    config_index,
                    result.prompt_content,
                    trace_metadata,
                )
                langfuse_attributes_context = (
                    self.langfuse_exporter.trace_attributes_context(config_index)
                )

            # Executa o framework com timeout de parede e ate `max_attempts`
            # tentativas. Uma config travada (ex.: Ollama sem responder) ou um
            # erro transitorio nao congela nem derruba o batch: aborta a
            # tentativa, tenta de novo e, esgotadas as tentativas, marca como
            # falha e segue para a proxima config.
            with langfuse_attributes_context:
                last_error: Optional[BaseException] = None
                for attempt in range(1, self.max_attempts + 1):
                    try:
                        with step_timeout(self.timeout_seconds):
                            start(config)
                        last_error = None
                        break
                    except StepTimeoutError as e:
                        last_error = e
                        retrying = attempt < self.max_attempts
                        suffix = " — tentando novamente..." if retrying else ""
                        self._log(
                            f"Timeout (tentativa {attempt}/{self.max_attempts}){suffix}"
                        )
                    except Exception as e:
                        last_error = e
                        retrying = attempt < self.max_attempts
                        suffix = " — tentando novamente..." if retrying else ""
                        self._log(
                            f"Erro (tentativa {attempt}/{self.max_attempts}): "
                            f"{type(e).__name__}: {e}{suffix}"
                        )

                if last_error is not None:
                    raise last_error

            # Lê o output gerado
            if os.path.exists(result.output_file):
                with open(result.output_file, "r", encoding="utf-8") as f:
                    result.output_content = f.read()

            result.success = True
            self._log(f"Sucesso!")

        except StepTimeoutError as e:
            result.error_message = f"{type(e).__name__}: {str(e)}"
            self._log("Timeout: pulando para a próxima config")

        except Exception as e:
            result.error_message = f"{type(e).__name__}: {str(e)}"
            self._log(f"Erro: {result.error_message}")
            if self.verbose:
                traceback.print_exc()

        finally:
            result.execution_time_seconds = time.time() - start_time
            result.timestamp = datetime.now()
            self._log(f"Tempo: {result.execution_time_seconds:.2f}s")

            if self.langfuse_exporter and self._run_name:
                self.langfuse_exporter.finish_trace(result, self._run_name)

        self.results.append(result)
        return result

    def run_batch(self, indices: list[int]) -> list[BenchmarkResult]:
        """
        Executa múltiplos benchmarks.

        Args:
            indices: Lista de índices (0-based)

        Returns:
            Lista de BenchmarkResults
        """
        total = len(indices)
        self._log(f"\nIniciando batch de {total} benchmark(s)...")
        self._log(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        if self.langfuse_exporter:
            self._run_name = self.langfuse_exporter.get_run_name()
            self._log(f"Langfuse run: {self._run_name}")

        batch_results = []
        for i, idx in enumerate(indices, 1):
            self._log(f"\n[{i}/{total}] ", )
            result = self.run_single(idx)
            batch_results.append(result)

        # Resumo
        self._log(f"\n{'='*60}")
        self._log("RESUMO DO BENCHMARK")
        self._log(f"{'='*60}")

        success_count = sum(1 for r in batch_results if r.success)
        total_time = sum(r.execution_time_seconds for r in batch_results)

        self._log(f"Total: {total}")
        self._log(f"Sucesso: {success_count}")
        self._log(f"Falhas: {total - success_count}")
        self._log(f"Tempo total: {total_time:.2f}s")
        self._log(f"Tempo médio: {total_time/total:.2f}s")

        if self.langfuse_exporter:
            self.langfuse_exporter.flush()

        return batch_results

    def get_results_as_dicts(self) -> list[dict]:
        """Retorna todos os resultados como lista de dicionários."""
        return [r.to_dict() for r in self.results]

    def clear_results(self):
        """Limpa os resultados acumulados."""
        self.results = []
