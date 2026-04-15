"""
Exportador de resultados de benchmark para o Langfuse.

Cria um Dataset no Langfuse espelhando a estrutura da planilha Google Sheets,
com suporte a anotação manual (Scores) e LLM-as-a-judge via Evaluators na UI.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .runner import BenchmarkResult

logger = logging.getLogger(__name__)

DATASET_NAME = "GithubDocs Benchmarks"

SCORE_CONFIGS = [
    {"name": "clareza", "data_type": "NUMERIC"},
    {"name": "completude", "data_type": "NUMERIC"},
    {"name": "concisão", "data_type": "NUMERIC"},
    {"name": "corretude", "data_type": "NUMERIC"},
]


def _is_langfuse_configured() -> bool:
    return bool(
        os.environ.get("LANGFUSE_PUBLIC_KEY")
        and os.environ.get("LANGFUSE_SECRET_KEY")
    )


class LangfuseExporter:
    """
    Exporta resultados do benchmark para o Langfuse usando a API de Datasets.

    Cada execução do benchmark cria um Dataset Run no Langfuse com um item por
    teste, reproduzindo a visão tabular da planilha Google Sheets.
    Scores (clareza, completude, concisão, corretude) podem ser preenchidos
    manualmente na UI do Langfuse ou via LLM-as-a-judge (Evaluators).

    O campo 'observação' é armazenado no campo `comment` de qualquer score.
    """

    def __init__(self, dataset_name: str = DATASET_NAME):
        from langfuse import Langfuse

        self.client = Langfuse()
        self.dataset_name = dataset_name
        # Maps config_index → active trace StatefulTraceClient
        self._active_traces: dict[int, object] = {}
        self._ensure_dataset()
        self._ensure_score_configs()

    def _ensure_dataset(self) -> None:
        """Cria o dataset se ainda não existir."""
        try:
            self.client.get_dataset(self.dataset_name)
        except Exception:
            try:
                self.client.create_dataset(
                    name=self.dataset_name,
                    description=(
                        "Resultados automáticos do benchmark GithubDocs. "
                        "Cada run corresponde a uma execução de python -m benchmark."
                    ),
                )
                logger.info("Dataset '%s' criado no Langfuse.", self.dataset_name)
            except Exception:
                logger.exception("Falha ao criar dataset '%s'.", self.dataset_name)

    def _ensure_score_configs(self) -> None:
        """Cria os score configs (clareza, completude, concisão, corretude) se necessário."""
        for cfg in SCORE_CONFIGS:
            try:
                self.client.create_score_config(
                    name=cfg["name"],
                    data_type=cfg["data_type"],
                )
            except Exception:
                # Já existe ou não suportado — ignora silenciosamente
                pass

    def get_run_name(self) -> str:
        """Gera um nome único para o dataset run baseado no timestamp atual."""
        return f"run-{datetime.now():%Y-%m-%d-%H%M%S}"

    def _get_or_create_dataset_item(
        self,
        config_index: int,
        prompt: Optional[str],
        metadata: dict,
    ) -> object:
        """Upsert de um dataset item com ID estável baseado no config_index."""
        item_id = f"config-{config_index + 1}"
        try:
            return self.client.create_dataset_item(
                dataset_name=self.dataset_name,
                input={"prompt": prompt or ""},
                metadata=metadata,
                id=item_id,
            )
        except Exception:
            logger.exception(
                "Falha ao criar/atualizar dataset item '%s'.", item_id
            )
            return None

    def start_trace(
        self,
        config_index: int,
        prompt: Optional[str],
        metadata: dict,
    ) -> Optional[str]:
        """
        Cria um trace Langfuse para o benchmark e armazena o trace_id
        em langfuse_integration para que o CallbackHandler do LangChain
        use-o como trace pai.

        Retorna o trace_id ou None se o Langfuse não estiver configurado.
        """
        from src.llm_agent.langfuse_integration import set_current_trace_id

        test_type = metadata.get("test_type", "unknown")
        model_name = metadata.get("model_name", "unknown")

        try:
            trace = self.client.trace(
                name=f"{test_type}-{model_name}",
                input={"prompt": prompt or ""},
                metadata=metadata,
                tags=[t for t in [test_type, model_name] if t and t != "unknown"],
            )
            self._active_traces[config_index] = trace
            set_current_trace_id(trace.id)
            return trace.id
        except Exception:
            logger.exception(
                "Falha ao criar trace Langfuse para config_index=%d.", config_index
            )
            return None

    def finish_trace(self, result: BenchmarkResult, run_name: str) -> None:
        """
        Atualiza o trace com os resultados finais e o vincula ao dataset item.
        Limpa o trace_id ativo em langfuse_integration.
        """
        from src.llm_agent.langfuse_integration import clear_current_trace_id

        clear_current_trace_id()

        trace = self._active_traces.pop(result.config_index, None)
        if trace is None:
            return

        output: dict = {}
        if result.output_content:
            output["content"] = result.output_content
        if result.error_message:
            output["error"] = result.error_message

        final_metadata = {
            "config_index": result.config_index + 1,
            "description": result.description,
            "commit_mixed": result.commit_mixed,
            "success": result.success,
            "execution_time_seconds": round(result.execution_time_seconds, 2),
            "model_name": result.model_name or "",
            "temperature": result.temperature,
            "repo_path": result.repo_path or "",
            "test_type": result.test_type or "",
            "error_message": result.error_message or "",
            "timestamp": result.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        }

        try:
            trace.update(
                output=output if output else None,
                metadata=final_metadata,
            )
        except Exception:
            logger.exception("Falha ao atualizar trace Langfuse.")

        item_metadata = {
            "description": result.description,
            "commit_mixed": result.commit_mixed,
            "test_type": result.test_type or "",
            "repo_path": result.repo_path or "",
            "model_name": result.model_name or "",
            "temperature": result.temperature,
        }
        dataset_item = self._get_or_create_dataset_item(
            result.config_index,
            result.prompt_content,
            item_metadata,
        )

        if dataset_item is not None:
            try:
                dataset_item.link(
                    trace,
                    run_name=run_name,
                    run_metadata={
                        "success": result.success,
                        "execution_time_seconds": round(result.execution_time_seconds, 2),
                        "model_name": result.model_name or "",
                        "timestamp": result.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    },
                )
            except Exception:
                logger.exception("Falha ao vincular trace ao dataset item.")

    def flush(self) -> None:
        """Garante que todos os eventos pendentes sejam enviados ao Langfuse."""
        try:
            self.client.flush()
        except Exception:
            logger.exception("Falha ao fazer flush do cliente Langfuse.")


def create_langfuse_exporter(dataset_name: str = DATASET_NAME) -> Optional[LangfuseExporter]:
    """
    Fábrica que retorna um LangfuseExporter se as chaves de ambiente estiverem
    configuradas, ou None caso contrário.
    """
    if not _is_langfuse_configured():
        return None
    try:
        return LangfuseExporter(dataset_name=dataset_name)
    except Exception:
        logger.exception("Falha ao inicializar LangfuseExporter.")
        return None
