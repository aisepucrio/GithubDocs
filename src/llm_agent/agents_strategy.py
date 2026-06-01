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
from .github_tools import get_github_issue_tools
from langchain_ollama import ChatOllama
from langchain_core.callbacks import BaseCallbackHandler
from langchain_classic.chains.summarize.chain import load_summarize_chain
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_classic.chains.summarize.chain import load_summarize_chain
from langchain_text_splitters import RecursiveCharacterTextSplitter
from .tools import ALL_TOOLS
from .langfuse_integration import append_langfuse_callback


def get_tools_from_names(names: list[str]):
    """Converts a list of tool names into a list of tool instances."""
    return [ALL_TOOLS[name] for name in names if name in ALL_TOOLS]


class LogLLMCallback(BaseCallbackHandler):
    def on_llm_start(self, serialized, prompts, **kwargs):
        print("LLM called (callback)")


class GeminiAgent(AIAgent):
    def __init__(self, model_name: str, api_key: str, base_prompt: str, temperature: float = 0.2, context_memory: InMemorySaver = None, tools: list[str] = None, base_url: str = ""):
        api_key = api_key or os.environ.get("GEMINI_API_KEY") or ""
        super().__init__(model_name, api_key, base_prompt, temperature, tools)

        self.chat_model: BaseChatModel = init_chat_model("google_genai:" + model_name, api_key=api_key, temperature=temperature)

    def generate_response(self, input: str) -> str:
        response = self.chat_model.invoke(
            self.base_prompt + "\n" + input,
            config=append_langfuse_callback(),
        )
        self.output = response.content
        return self.output

    def generate_response_with_prompt(self, prompt: str, input: str, config: dict = None) -> str:
        response = self.chat_model.invoke(
            prompt + "\n" + input,
            config=append_langfuse_callback(config),
        )
        self.output = response.content
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
    def __init__(self, model_name: str, api_key: str, base_prompt: str, temperature: float = 0.2, context_memory: InMemorySaver = None, tools: list[str] = None, base_url: str = ""):
        api_key = api_key or os.environ.get("OPENAI_API_KEY") or ""
        super().__init__(model_name, api_key, base_prompt, temperature, tools)
        self.chat_model: BaseChatModel = init_chat_model("openai:" + model_name, api_key=api_key)

        try:
            self.chat_model = self.chat_model.bind_tools(get_github_issue_tools())
        except Exception:
            pass

    def generate_response(self, input: str) -> str:
        full_input = self.base_prompt + "\n" + input
        response = self.chat_model.invoke(
            full_input,
            config=append_langfuse_callback(),
        )

        if hasattr(response, "tool_calls") and response.tool_calls:
            return self._handle_tool_calls_gpt(response, full_input)

        self.output = response.content
        return self.output

    def generate_response_with_prompt(self, prompt: str, input: str, config: dict = None) -> str:
        full_input = prompt + "\n" + input
        response = self.chat_model.invoke(
            full_input,
            config=append_langfuse_callback(config),
        )

        if hasattr(response, "tool_calls") and response.tool_calls:
            return self._handle_tool_calls_gpt(response, full_input)

        self.output = response.content
        return self.output

    def _handle_tool_calls_gpt(self, response, original_input: str) -> str:
        from langchain_core.messages import HumanMessage, ToolMessage

        messages = [
            HumanMessage(content=original_input),
            response,
        ]

        tools = {t.name: t for t in get_github_issue_tools()}
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            if tool_name in tools:
                tool_result = tools[tool_name].invoke(tool_args)
                messages.append(
                    ToolMessage(
                        content=str(tool_result),
                        tool_call_id=tool_call["id"],
                    )
                )

        final_response = self.chat_model.invoke(
            messages,
            config=append_langfuse_callback(),
        )
        self.output = final_response.content
        return self.output

    def _count_tokens(self, input: str) -> int:
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(input))


class OllamaAgent(AIAgent):
    def __init__(self, model_name: str, api_key: str, base_prompt: str, temperature: float = 0.2, context_memory: InMemorySaver = None, tools: list[str] = None, base_url: str = ""):
        super().__init__(model_name, api_key, base_prompt, temperature, tools)

        resolved_url = base_url or os.environ.get("OLLAMA_HOST", "http://localhost:11434")

        self.chat_model: BaseChatModel = ChatOllama(
            model=model_name,
            base_url=resolved_url,
            temperature=temperature,
            callbacks=[LogLLMCallback()],
        )

        actual_tools = get_tools_from_names(self.tools) if self.tools else []

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

    def generate_response(self, input: str) -> str:
        full_prompt = self.base_prompt + "\n" + input
        response = self.agent.invoke(
            {"messages": [("user", full_prompt)]},
            config=append_langfuse_callback(),
        )
        self.output = response["messages"][-1].content
        return self.output

    def generate_response_with_prompt(self, prompt: str, input: str, config: dict | None = None) -> str:
        print("Using Ollama agent")
        full_prompt = prompt + "\n" + input
        response = self.agent.invoke(
            {"messages": [("user", full_prompt)]},
            config=append_langfuse_callback(config),
        )
        self.output = response["messages"][-1].content
        return self.output

    def refine_content(self, text: str) -> str:
        chunk_size = self.context_window // 4
        splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=100)
        docs = [Document(page_content=c) for c in splitter.split_text(text)]
        chain = load_summarize_chain(self.chat_model, chain_type="refine",verbose=True)
        return chain.invoke(docs)["output_text"]

    def _count_tokens(self, input: str) -> int:
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(input))


class MockAgent(AIAgent):
    def __init__(self, model_name: str, api_key: str, base_prompt: str, temperature: float = 0.2, context_memory: InMemorySaver = None, tools: list = None, base_url: str = ""):
        super().__init__(model_name, api_key, base_prompt, temperature, tools)

    def generate_response(self, input: str) -> str:
        print("--- MOCK AGENT ---")
        print("Prompt:", self.base_prompt.encode("utf-8", errors="ignore"))
        print("Input:", input)
        print("--- END MOCK AGENT ---")
        return "Mocked response"

    def generate_response_with_prompt(self, prompt: str, input: str, config: dict = None) -> str:
        print("--- MOCK AGENT ---")
        prompt = prompt.encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")
        print("Prompt:", f"{prompt}")
        print("Input:", input)
        print("--- END MOCK AGENT ---")
        return "Mocked response with custom prompt"

    def refine_content(self, text: str) -> str:
        print("--- MOCK AGENT ---")
        print("Refining content:", text)
        print("--- END MOCK AGENT ---")
        return "Refined content (mocked)"
    
    def refine_content(self, text: str) -> str:
        print("--- MOCK AGENT ---")
        print("Refining content:", text)
        print("--- END MOCK AGENT ---")
        return "Refined content (mocked)"

    def _count_tokens(self, input: str) -> int:
        return len(input.split())


def get_agent_dictionary() -> dict:
    return {
        "gemini": GeminiAgent,
        "gpt": GPTAgent,
        "ollama": OllamaAgent,
        "mock": MockAgent,
    }
