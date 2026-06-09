import os
from langchain_core.documents import Document

import tiktoken
from openai import OpenAI

from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents.middleware import SummarizationMiddleware
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.language_models.chat_models import BaseChatModel
from .agent_interface import AIAgent
from langchain_ollama import ChatOllama
from langchain_core.callbacks import BaseCallbackHandler
from langchain_classic.chains.summarize.chain import load_summarize_chain
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_classic.chains.summarize.chain import load_summarize_chain
from langchain_text_splitters import RecursiveCharacterTextSplitter


def content_to_text(content) -> str:
    """Normaliza response.content (str | list[str|dict]) para str.

    Modelos como Gemini podem devolver content como lista de blocos
    (ex.: thinking + texto). Concatenamos apenas as partes textuais.
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                if block.get("type") == "text" and "text" in block:
                    parts.append(block["text"])
                elif "text" in block:
                    parts.append(block["text"])
        return "".join(parts)
    return str(content)


class GeminiAgent(AIAgent):
    def __init__(self, model_name: str, api_key: str, base_prompt: str, temperature: float = 0.2, context_memory: InMemorySaver = None):
        api_key  = api_key or os.environ.get("GEMINI_API_KEY") or ""
        super().__init__(model_name, api_key, base_prompt, temperature, context_memory)

        self.chat_model:BaseChatModel = init_chat_model("google_genai:" + model_name, api_key=api_key, temperature=temperature)

    def generate_response(self, input: str) -> str:
        callbacks = []
        langfuse_cb = self._langfuse_callback
        if langfuse_cb:
            callbacks.append(langfuse_cb)

        response = self.chat_model.invoke(
            self.base_prompt + "\n" + input,
            config={"callbacks": callbacks} if callbacks else None
        )
        self.output = content_to_text(response.content)
        return self.output

    def generate_response_with_prompt(self,  prompt: str, input: str, config: dict = None) -> str:
        config = config or {}
        callbacks = config.get("callbacks", [])
        langfuse_cb = self._langfuse_callback
        if langfuse_cb and langfuse_cb not in callbacks:
            callbacks.append(langfuse_cb)
        config["callbacks"] = callbacks

        response = self.chat_model.invoke(
             prompt + "\n" + input,
             config=config if config["callbacks"] else None
        )
        self.output = content_to_text(response.content)
        return self.output

    def refine_content(self, text: str) -> str:
        chunk_size = self.context_window // 4
        splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=100)
        docs = [Document(page_content=c) for c in splitter.split_text(text)]
        chain = load_summarize_chain(self.chat_model, chain_type="refine",verbose=True)
        return chain.invoke(docs)["output_text"]

    def _count_tokens(self, input: str) -> int:
        return self.chat_model.get_num_tokens(self.base_prompt + "\n" + input)
class GPTAgent(AIAgent):
    def __init__(self, model_name: str, api_key: str, base_prompt: str, temperature: float = 0.2, context_memory: InMemorySaver = None):
        api_key = api_key or os.environ.get("OPENAI_API_KEY") or ""
        super().__init__(model_name, api_key, base_prompt, temperature, context_memory)
        self.chat_model: BaseChatModel = init_chat_model("openai:" + model_name, api_key=api_key)

    def generate_response(self, input: str) -> str:
        full_input = self.base_prompt + "\n" + input
        kwargs = {}
        if not (self.model_name.startswith("gpt-5") or self.model_name.startswith("o")):
            kwargs["temperature"] = self.temperature
        response = self.chat_model.invoke(full_input, **kwargs)

        self.output = content_to_text(response.content)
        return self.output

    def generate_response_with_prompt(self, prompt: str, input: str, config: dict = None) -> str:
        full_input = prompt + "\n" + input
        kwargs = {}
        if not (self.model_name.startswith("gpt-5") or self.model_name.startswith("o")):
            kwargs["temperature"] = self.temperature
        response = self.chat_model.invoke(full_input, **kwargs)

        self.output = content_to_text(response.content)
        return self.output

    def _count_tokens(self, input: str) -> int:
        encoding = tiktoken.get_encoding("cl100k_base")
        num_tokens = len(encoding.encode(input))
        return num_tokens

#  ollama aqui -----V

class OllamaAgent(AIAgent):
    def __init__(self, model_name: str, api_key: str, base_prompt: str, temperature: float = 0.2, context_memory: InMemorySaver = None):
        super().__init__(model_name, api_key, base_prompt, temperature, context_memory)
        # self.client = ollama.Client()

        # Reusa a instancia unica de _langfuse_callback (definida na base AIAgent).
        # invoke_with_tools tambem a injeta no config; sendo o mesmo objeto, o LangChain deduplica.
        cb = [self._langfuse_callback] if self._langfuse_callback else []

        self.chat_model: BaseChatModel = ChatOllama(
            model=model_name,
            base_url=os.environ.get("OLLAMA_URL", "http://localhost:11434"),
            temperature=temperature,
            callbacks=cb
        )

        # Construido lazy: invoke_with_tools (base) cria seu proprio executor sem essa middleware.
        self._default_agent = None

    def _get_default_agent(self):
        if self._default_agent is None:
            self._default_agent = create_agent(
                self.chat_model,
                tools=[],
                middleware=[
                    SummarizationMiddleware(
                        model=f"ollama:{self.model_name}",
                        trigger=("tokens", 4000),
                        keep=("messages", 20),
                    )
                ],
                checkpointer=self.context_memory,
            )
        return self._default_agent

    def generate_response_with_prompt(self, prompt, input, config: dict | None = None):

        full_prompt = prompt + "\n" + input
        response = self._get_default_agent().invoke(
            {"messages": [("user", full_prompt)]},
            config=config

        )
        self.output = content_to_text(response["messages"][-1].content)
        return self.output

    # funcao aparentemente nao usada
    #  TODO
    def generate_response(self, input: str) -> str:
        full_prompt = self.base_prompt + "\n" + input
        response = self._get_default_agent().invoke(
            {"messages": [("user", full_prompt)]}
        )
        self.output = content_to_text(response["messages"][-1].content)
        return self.output

    def refine_content(self, text: str) -> str:
        chunk_size = self.context_window // 4
        splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=100)
        docs = [Document(page_content=c) for c in splitter.split_text(text)]
        chain = load_summarize_chain(self.chat_model, chain_type="refine",verbose=True)
        return chain.invoke(docs)["output_text"]

    def _count_tokens(self, input: str) -> int:
         # Naive token counting logic
         return len(input.split()) // 3


class MockAgent(AIAgent):
    def __init__(self, model_name: str, api_key: str, base_prompt: str, temperature: float = 0.2, context_memory: InMemorySaver = None):
        super().__init__(model_name, api_key, base_prompt, temperature, context_memory)

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
    
    def refine_content(self, text: str) -> str:
        print("--- MOCK AGENT ---")
        print("Refining content:", text)
        print("--- END MOCK AGENT ---")
        return "Refined content (mocked)"

    def invoke_with_tools(self, prompt: str, tools: list, config: dict = None) -> str:
        print("--- MOCK AGENT TOOL CALLING ---")
        print("Prompt:", prompt[:200])
        print("Tools:", [getattr(t, "name", repr(t)) for t in tools])
        print("--- END MOCK AGENT ---")
        return "Mocked tool-calling response"

    def _count_tokens(self, input: str) -> int:
        return len(input.split())

def get_agent_dictionary() -> dict:
    return {
        "gemini": GeminiAgent,
        "gpt": GPTAgent,
        "ollama": OllamaAgent,
        "mock": MockAgent,
    }