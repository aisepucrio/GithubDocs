from abc import ABC, abstractmethod
from llm_agent.context_window_size import LLM_CONTEXT_WINDOWS

class AIAgent(ABC):
    def __init__(self, model_name: str, api_key: str, base_prompt: str):
        self.model_name = model_name
        self.api_key = api_key
        self.base_prompt = base_prompt
        self.context_window = LLM_CONTEXT_WINDOWS[self.model_name]

    @abstractmethod
    def generate_response(self, input: str) -> str:
        pass

    @abstractmethod
    def _count_tokens(self, input: str) -> int:
        pass
    
    def _get_model_window_context(self) -> int:
        return self.context_window
    
    def need_summarization(self, input: str) -> bool:
        return self._count_tokens(input) > self.context_window