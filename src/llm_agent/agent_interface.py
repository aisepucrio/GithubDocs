from abc import ABC, abstractmethod
from .context_window_size import LLM_CONTEXT_WINDOWS
from .langfuse_integration import get_langfuse_callback
from typing import List, Dict
from langgraph.checkpoint.memory import InMemorySaver


def _message_content_to_str(content) -> str:
    """Normaliza AIMessage.content para str (Gemini pode retornar list[dict] com content blocks)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "".join(parts)
    return str(content) if content is not None else ""


class AIAgent(ABC):
    def __init__(self, model_name: str, api_key: str, base_prompt: str, temperature: float, context_memory: InMemorySaver = None):
        self.model_name = model_name
        self.api_key = api_key
        self.base_prompt = base_prompt
        self.context_window = LLM_CONTEXT_WINDOWS[self.model_name]
        self.output = ""
        self.temperature = temperature
        self.context_memory = context_memory
        # Memoize Langfuse callback handler per agent instance to avoid repeated initialization.
        # Single shared instance: LangChain dedups it across local + inheritable callbacks.
        self._langfuse_callback = get_langfuse_callback()
        #variables for the interative one
        self.mode = 0  # 0: non-interactive, 1: interactive
        self.chat_history: List[Dict[str, str]] = []


    @abstractmethod
    def generate_response(self, input: str) -> str:
        pass

    @abstractmethod
    def generate_response_with_prompt(self, prompt: str, input: str, config: dict = None) -> str:
        pass
    
    @abstractmethod
    def refine_content(self, text: str) -> str:
        pass

    @abstractmethod
    def _count_tokens(self, input: str) -> int:
        pass

    def invoke_with_tools(self, prompt: str, tools: list, config: dict = None) -> str:
        """Executa um turno ReAct: agent_executor sobre self.chat_model com as tools. MockAgent sobrescreve."""
        from langchain.agents import create_agent

        # Injeta o callback do Langfuse nos callbacks do invoke (inheritable), para que o
        # trace cubra toda a arvore do agente (grafo -> LLM -> tools), nao so a chamada do modelo.
        config = config or {}
        callbacks = config.get("callbacks", [])
        if self._langfuse_callback and self._langfuse_callback not in callbacks:
            callbacks.append(self._langfuse_callback)
        config["callbacks"] = callbacks

        executor = create_agent(self.chat_model, tools=tools, checkpointer=self.context_memory)
        response = executor.invoke({"messages": [("user", prompt)]}, config=config)
        return _message_content_to_str(response["messages"][-1].content)

    def _get_model_window_context(self) -> int:
        return self.context_window
    
    def need_summarization(self, input: str) -> bool:
        return self._count_tokens(input) > self.context_window