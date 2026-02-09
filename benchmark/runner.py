"""
Runner de benchmark - executa os testes e coleta métricas.
"""

import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import tomllib
import sys
import os

# Adiciona o diretório pai ao path para importar GithubDocs
BENCHMARK_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(BENCHMARK_DIR)  # githubdocs/
GITHUBDOCS_DIR = os.path.join(PARENT_DIR, "GithubDocs")  # for internal src imports
sys.path.insert(0, PARENT_DIR)
sys.path.insert(0, GITHUBDOCS_DIR)

from src.facade import start, render_prompt
from src.load_configuration.conf_structures import BaseAppConfig
from src.repo_info_extraction import RepoInfoExtractor

from .test_configs import ConfigMetadata


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

    def to_dict(self) -> dict:
        """Converte para dicionário para exportação."""
        return {
            "config_index": self.config_index + 1,  # 1-based para usuário
            "description": self.description,
            "commit_mixed": "Sim" if self.commit_mixed else "Não",
            "success": "Sim" if self.success else "Não",
            "execution_time_seconds": round(self.execution_time_seconds, 2),
            "output_file": self.output_file or "",
            "error_message": self.error_message or "",
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "model_name": self.model_name or "",
            "temperature": self.temperature if self.temperature is not None else "",
            "repo_path": self.repo_path or "",
            "prompt_content": self.prompt_content or "",
            "test_type": self.test_type or "",
        }


class BenchmarkRunner:
    """Executa benchmarks de configs."""

    def __init__(
        self,
        configs: list[str],
        names: list[str],
        metadata: Optional[list[ConfigMetadata]] = None,
        verbose: bool = True,
    ):
        """
        Args:
            configs: Lista de strings TOML com as configurações
            names: Lista de nomes descritivos para cada config
            metadata: Lista de metadados (description, commit_mixed) para cada config
            verbose: Se True, imprime logs detalhados
        """
        self.configs = configs
        self.names = names
        self.metadata = metadata or [ConfigMetadata() for _ in configs]
        self.verbose = verbose
        self.results: list[BenchmarkResult] = []

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

            # Captura o prompt renderizado antes de executar
            try:
                extractor = RepoInfoExtractor(
                    repository_path=config.target_info.repo_path,
                    commit_list=config.target_info.commit_list,
                    target_branch=config.target_info.branch_name,
                    ignored_files=config.target_info.ignore_files
                )
                repo_info = extractor.extract_repo_info()

                if config.orchestration_steps:
                    step = config.orchestration_steps[0]
                    template_vars = step.prompt_variables.copy()
                    template_vars['repo_info'] = repo_info
                    result.prompt_content = render_prompt(
                        step.template_path,
                        step.prompt_file,
                        template_vars,
                        repo_info["repo_path"]
                    )
            except Exception as prompt_err:
                self._log(f"Aviso: Não foi possível capturar o prompt: {prompt_err}")

            # Executa o framework
            start(config)

            # Lê o output gerado
            if os.path.exists(result.output_file):
                with open(result.output_file, "r", encoding="utf-8") as f:
                    result.output_content = f.read()

            result.success = True
            self._log(f"Sucesso!")

        except Exception as e:
            result.error_message = f"{type(e).__name__}: {str(e)}"
            self._log(f"Erro: {result.error_message}")
            if self.verbose:
                traceback.print_exc()

        finally:
            result.execution_time_seconds = time.time() - start_time
            result.timestamp = datetime.now()
            self._log(f"Tempo: {result.execution_time_seconds:.2f}s")

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

        return batch_results

    def get_results_as_dicts(self) -> list[dict]:
        """Retorna todos os resultados como lista de dicionários."""
        return [r.to_dict() for r in self.results]

    def clear_results(self):
        """Limpa os resultados acumulados."""
        self.results = []