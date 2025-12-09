import os

import tiktoken
import ollama 

from openai import OpenAI
from google import genai

from .agent_interface import AIAgent

class GeminiAgent(AIAgent):
    def __init__(self, model_name: str, api_key: str, base_prompt: str, temperature: float = 0.2):
        api_key = api_key or os.environ.get("GEMINI_API_KEY")
        super().__init__(model_name, api_key, base_prompt, temperature)
        self.client: genai.Client = genai.Client(api_key=self.api_key)

    def generate_response(self, input: str) -> str:
        response = self.client.models.generate_content(
            model=self.model_name, contents=self.base_prompt + "\n" + input,
            config={"temperature": self.temperature}
        )
        self.output = response.text
        return self.output
    
    def generate_response_with_prompt(self, prompt: str, input: str) -> str:
        response = self.client.models.generate_content(
            model=self.model_name, contents=prompt + "\n" + input,
            config={"temperature": self.temperature}
        )
        self.output = response.text
        return self.output

    def _count_tokens(self, input: str) -> int:
        return self.client.models.count_tokens(
            model=self.model_name, contents=self.base_prompt + "\n" + input
        ).total_tokens

class GPTAgent(AIAgent):
    def __init__(self, model_name: str, api_key: str, base_prompt: str, temperature: float = 0.2):
        api_key = api_key or os.environ.get("OPENAI_API_KEY")
        super().__init__(model_name, api_key, base_prompt, temperature)
        self.client: OpenAI = OpenAI(api_key=self.api_key)

    def generate_response(self, input: str) -> str:
        parameters = {
            "model": self.model_name,
            "input": self.base_prompt + "\n" + input,
        }
        if not self.model_name.startswith("gpt-5") or self.model_name.startswith("o"):
            parameters["temperature"] = self.temperature
        response = self.client.responses.create(**parameters)
        self.output = response.output_text
        return self.output

    def generate_response_with_prompt(self, prompt: str, input: str) -> str:
        parameters = {
            "model": self.model_name,
            "input": prompt + "\n" + input,
        }
        if not self.model_name.startswith("gpt-5") or self.model_name.startswith("o"):
            parameters["temperature"] = self.temperature
        response = self.client.responses.create(**parameters)
        self.output = response.output_text
        return self.output

    def _count_tokens(self, input: str) -> int:
        encoding = tiktoken.get_encoding("cl100k_base")
        num_tokens = len(encoding.encode(input))
        return num_tokens

class OllamaAgent(AIAgent):
    def __init__(self, model_name: str, api_key: str, base_prompt: str, temperature: float = 0.2):
        super().__init__(model_name, api_key, base_prompt, temperature)
        self.client = ollama.Client()

    def generate_response_with_prompt(self, prompt, input):
        full_prompt = prompt + "\n" + input
        response = self.client.chat(
            model=self.model_name, 
            messages=[
                {"role": "user", "content": full_prompt},
            ],
            options={
                "num_ctx": self.context_window,
                "num_predict": -1,
                "temperature": self.temperature,
            },
            stream=False,
            think=False
        )
        self.output = response.message.content
        return self.output

    def generate_response(self, prompt: str, input: str) -> str:
        full_prompt = self.base_prompt + "\n" + input
        response = self.client.chat(
            model=self.model_name, 
            messages=[
                {"role": "user", "content": full_prompt},
            ],
            options={
                "num_ctx": self.context_window,
                "num_predict": -1,
                "temperature": self.temperature,
            },
            stream=False,
            think=False
        )
        self.output = response.message.content
        return self.output

    def _count_tokens(self, input: str) -> int:
         # Naive token counting logic
         return len(input.split())/3


class MockAgent(AIAgent):
    def __init__(self, model_name: str, api_key: str, base_prompt: str, temperature: float = 0.2):
        super().__init__(model_name, api_key, base_prompt, temperature)

    def generate_response(self, input: str) -> str:
        print("--- MOCK AGENT ---")
        print("Prompt:", self.base_prompt.encode('utf-8', errors='ignore'))
        print("Input:", input)
        print("--- END MOCK AGENT ---")
        return "Mocked response"

    def generate_response_with_prompt(self, prompt: str, input: str) -> str:
        print("--- MOCK AGENT ---")
        prompt = prompt.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
        print("Prompt:", f'{prompt}')
        print("Input:", input)
        print("--- END MOCK AGENT ---")
        return "Mocked response with custom prompt"

    def _count_tokens(self, input: str) -> int:
        return len(input.split())

def get_agent_dictionary() -> dict:
    return {
        "gemini": GeminiAgent,
        "gpt": GPTAgent,
        "ollama": OllamaAgent,
        "mock": MockAgent,
    }