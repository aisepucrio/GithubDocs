from .ai_agent_interface import AIAgent
from google import genai

from openai import OpenAI
import tiktoken

class GeminiAgent(AIAgent):
    def __init__(self, model_name: str, api_key: str, base_prompt: str):
        super().__init__(model_name, api_key, base_prompt)
        self.client: genai.Client = genai.Client(api_key=self.api_key)

    def generate_response(self, input: str) -> str:
        response = self.client.models.generate_content(
            model=self.model_name, contents=self.base_prompt + "\n" + input
        )
        self.output = response.text
        return self.output

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
        self.output = response.output_text
        return self.output

    def _count_tokens(self, input: str) -> int:
        encoding = tiktoken.get_encoding("cl100k_base")
        num_tokens = len(encoding.encode(input))
        return num_tokens
    

if __name__ == "__main__":
    gemini_agent = GeminiAgent("gemini-2.0-flash-lite", "AIzaSyBJssh_vtQZBPFceyhWy4aGkYxwbn2T6MA", "This is a base prompt for Gemini.")
    gemini_agent.generate_response("Hello, how are you?")
    print(f"Gemini Agent Response: {gemini_agent.output}")
    print(f"Gemini Agent Token Count: {gemini_agent._get_model_window_context()}")
