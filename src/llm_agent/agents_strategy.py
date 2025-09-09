from llm_agent.ai_agent_interface import AIAgent
from google import genai

from openai import OpenAI
import tiktoken

class GeminiAgent(AIAgent):
    def __init__(self, model_name: str, api_key: str, base_prompt: str):
        super().__init__(model_name, api_key, base_prompt)
        self.client: genai.Client = genai.Client()

    def generate_response(self, input: str) -> str:
        response = self.client.models.generate_content(
            model=self.model_name, contents=self.base_prompt + "\n" + input
        )
        return response.text

    def _count_tokens(self, input: str) -> int:
        return self.client.models.count_tokens(
            model=self.model_name, contents=self.base_prompt + "\n" + input
        ).total_tokens

class GPTAgent(AIAgent):
    def __init__(self, model_name: str, api_key: str, base_prompt: str):
        super().__init__(model_name, api_key, base_prompt)
        self.client: OpenAI = OpenAI(api_key=self.api_key)

    def generate_response(self, input: str) -> str:
        response = self.client.responses.create(
            model=self.model_name,
            input=self.base_prompt + "\n" + input,
        )
        return response.output_text

    def _count_tokens(self, input: str) -> int:
        encoding = tiktoken.get_encoding("cl100k_base")
        num_tokens = len(encoding.encode(input))
        return num_tokens
