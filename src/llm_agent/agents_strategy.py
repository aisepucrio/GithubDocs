from .agent_interface import AIAgent
from google import genai
import os
from openai import OpenAI
import tiktoken

from ollama import chat
from ollama import ChatResponse

class GeminiAgent(AIAgent):
    def __init__(self, model_name: str, api_key: str, base_prompt: str):
        api_key = api_key or os.environ.get("GEMINI_API_KEY")
        super().__init__(model_name, api_key, base_prompt)
        self.client: genai.Client = genai.Client(api_key=self.api_key)

    def generate_response(self, input: str) -> str:
        response = self.client.models.generate_content(
            model=self.model_name, contents=self.base_prompt + "\n" + input
        )
        self.output = response.text
        return self.output
    
    def generate_response_with_prompt(self, prompt: str, input: str) -> str:
        response = self.client.models.generate_content(
            model=self.model_name, contents=prompt + "\n" + input
        )
        self.output = response.text
        return self.output

    def _count_tokens(self, input: str) -> int:
        return self.client.models.count_tokens(
            model=self.model_name, contents=self.base_prompt + "\n" + input
        ).total_tokens

class GPTAgent(AIAgent):
    def __init__(self, model_name: str, api_key: str, base_prompt: str):
        api_key = api_key or os.environ.get("OPENAI_API_KEY")
        super().__init__(model_name, api_key, base_prompt)
        self.client: OpenAI = OpenAI(api_key=self.api_key)

    def generate_response(self, input: str) -> str:
        response = self.client.responses.create(
            model=self.model_name,
            input=self.base_prompt + "\n" + input,
        )
        self.output = response.output_text
        return self.output

    def generate_response_with_prompt(self, prompt: str, input: str) -> str:
        response = self.client.responses.create(
            model=self.model_name,
            input=prompt + "\n" + input,
        )
        self.output = response.output_text
        return self.output

    def _count_tokens(self, input: str) -> int:
        encoding = tiktoken.get_encoding("cl100k_base")
        num_tokens = len(encoding.encode(input))
        return num_tokens

class OllamaAgent(AIAgent):
    def __init__(self, model_name: str, api_key: str, base_prompt: str):
        super().__init__(model_name, api_key, base_prompt)

    def generate_response_with_prompt(self, prompt, input):
        full_prompt = prompt + "\n" + input
        response: ChatResponse = chat(
            model=self.model_name,
            prompt=full_prompt
        )
        self.output = response.message.content
        return self.output

    # def generate_response(self, prompt: str, input: str) -> str:
    #     # Placeholder for Ollama API call with custom prompt
    #     self.output = "Ollama response placeholder with custom prompt"
    #     return self.output

    # def _count_tokens(self, input: str) -> int:
    #     # Placeholder for token counting logic
    #     return len(input.split())


class MockAgent(AIAgent):
    def __init__(self, model_name: str, api_key: str, base_prompt: str):
        super().__init__(model_name, api_key, base_prompt)

    def generate_response(self, input: str) -> str:
        print("--- MOCK AGENT ---")
        print("Prompt:", self.base_prompt)
        print("Input:", input)
        print("--- END MOCK AGENT ---")
        return "Mocked response"

    def generate_response_with_prompt(self, prompt: str, input: str) -> str:
        print("--- MOCK AGENT ---")
        print("Prompt:", prompt)
        print("Input:", input)
        print("--- END MOCK AGENT ---")
        return "Mocked response with custom prompt"

    def _count_tokens(self, input: str) -> int:
        return len(input.split())

def get_agent_dictionary() -> dict:
    return {
        "gemini": GeminiAgent,
        "gpt": GPTAgent,
        "mock": MockAgent,
    }