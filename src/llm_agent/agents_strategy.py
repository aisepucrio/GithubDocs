import os

import tiktoken
# import ollama 

from openai import OpenAI

from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents.middleware import SummarizationMiddleware
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.language_models.chat_models import BaseChatModel
from .agent_interface import AIAgent
from langchain_ollama import ChatOllama
from langchain_core.callbacks import BaseCallbackHandler

from .tools import ALL_TOOLS

def get_tools_from_names(names: list[str]):
    """Converte lista de nomes em lista de tools"""
    return [ALL_TOOLS[name] for name in names if name in ALL_TOOLS]

class LogLLMCallback(BaseCallbackHandler):
    def on_llm_start(self, serialized, prompts, **kwargs):
        print("🔥 LLM CHAMADO (callback)")



class GeminiAgent(AIAgent):
    def __init__(self, model_name: str, api_key: str, base_prompt: str, temperature: float = 0.2, context_memory: InMemorySaver = None):
        api_key  = api_key or os.environ.get("GEMINI_API_KEY") or ""
        super().__init__(model_name, api_key, base_prompt, temperature)

        self.chat_model: BaseChatModel = init_chat_model(
            "google_genai:" + model_name,
            api_key=api_key,
            temperature=temperature
        )

        self.agent = create_agent(
            self.chat_model,
            tools=[],
            middleware=[
            SummarizationMiddleware(
            model="google_genai:" + model_name,
            trigger=("tokens", 4000),
            keep=("messages", 20),
            ),],
            checkpointer=context_memory
        )


    def generate_response(self, input: str) -> str:
        response = self.agent.invoke(
            {"messages": [("user", self.base_prompt + "\n" + input)]}
        )
        self.output = response["messages"][-1].content
        return self.output

    def generate_response_with_prompt(self, prompt: str, input: str, config: dict = None) -> str:
        response = self.agent.invoke(
            {"messages": [("user", prompt + "\n" + input)]},
            config=config
        )
        self.output = response["messages"][-1].content
        return self.output

    def _count_tokens(self, input: str) -> int:
        return self.chat_model.get_num_tokens(self.base_prompt + "\n" + input)

class GPTAgent(AIAgent):
    def __init__(self, model_name: str, api_key: str, base_prompt: str, temperature: float = 0.2, context_memory: InMemorySaver = None):
        api_key = api_key or os.environ.get("OPENAI_API_KEY") or ""
        super().__init__(model_name, api_key, base_prompt, temperature)
        self.chat_model: BaseChatModel = init_chat_model("openai:" + model_name, api_key=api_key)

    def generate_response(self, input: str) -> str:
        parameters = {
            "model": self.model_name,
            "input": self.base_prompt + "\n" + input,
        }
        if not self.model_name.startswith("gpt-5") or self.model_name.startswith("o"):
            parameters["temperature"] = self.temperature
        response = self.chat_model.invoke(**parameters)
        self.output = response.content
        return self.output

    def generate_response_with_prompt(self, prompt: str, input: str, config: dict = None) -> str:
        parameters = {
            "model": self.model_name,
            "input": prompt + "\n" + input,
        }
        if not self.model_name.startswith("gpt-5") or self.model_name.startswith("o"):
            parameters["temperature"] = self.temperature
        response = self.chat_model.invoke(**parameters)
        self.output = response.content
        return self.output

    def _count_tokens(self, input: str) -> int:
        encoding = tiktoken.get_encoding("cl100k_base")
        num_tokens = len(encoding.encode(input))
        return num_tokens

#  ollama aqui -----V

class OllamaAgent(AIAgent):
    def __init__(self, model_name: str, api_key: str, base_prompt: str, temperature: float = 0.2, context_memory: InMemorySaver = None, tools: list[str] = None):
        super().__init__(model_name, api_key, base_prompt, temperature, tools)
        # self.client = ollama.Client()

        self.chat_model: BaseChatModel = ChatOllama(
            model=model_name,
            base_url="http://localhost:11434",
            temperature=temperature,
            callbacks=[LogLLMCallback()]
        )

        actual_tools = get_tools_from_names(self.tools) if self.tools else []
        print("actual tools: ", actual_tools)

        self.agent = create_agent(
            self.chat_model,
            tools=actual_tools,  
            middleware=[
                SummarizationMiddleware(
                    model=f"ollama:{model_name}",
                    trigger=("tokens", 4000),
                    keep=("messages", 20),
                )
            ],
            checkpointer=context_memory,
        )

    def generate_response_with_prompt(self, prompt, input, config: dict | None = None):
        # print(" COM PROMPT")
        # print("está sendo chamada")
        print("🔥 using ollama 🔥") 
        full_prompt = prompt + "\n" + input
        response =self.agent.invoke(
            {"messages": [("user", full_prompt)]},
            config=config

        )
        self.output  = response["messages"][-1].content
        return self.output

    # funcao aparentemente nao usada
    #  TODO 
    def generate_response(self, prompt: str, input: str) -> str:
        full_prompt = self.base_prompt + "\n" + input
        response = self.agent.invoke(
            {"messages": full_prompt}
        )
        self.output = response["messages"][-1].content
        return self.output

    def _count_tokens(self, input: str) -> int:
         # Naive token counting logic
        #  return len(input.split())/3
        full_text = self.base_prompt + "\n" + input
        # estimativa simples: ~3 caracteres por token
        return len(full_text) // 3



class MockAgent(AIAgent):
    def __init__(self, model_name: str, api_key: str, base_prompt: str, temperature: float = 0.2, context_memory: InMemorySaver = None,  tools: list = None):
        super().__init__(model_name, api_key, base_prompt, temperature)

    def generate_response(self, input: str) -> str:
        print("--- MOCK AGENT ---")
        print("Prompt:", self.base_prompt.encode('utf-8', errors='ignore'))
        print("Input:", input)
        print("--- END MOCK AGENT ---")
        return "Mocked response"

    def generate_response_with_prompt(self, prompt: str, input: str, config: dict = None) -> str:
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