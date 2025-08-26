from pedro_adapt.ai_agent import AIAgent
from google import genai

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
        )
