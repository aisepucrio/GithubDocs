import os

import tiktoken
import ollama 

from openai import OpenAI

from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.language_models.chat_models import BaseChatModel

from .agent_interface import AIAgent
from .github_tools import get_github_issue_tools

class GeminiAgent(AIAgent):
    def __init__(self, model_name: str, api_key: str, base_prompt: str, temperature: float = 0.2):
        api_key = api_key or os.environ.get("GEMINI_API_KEY")
                
        super().__init__(model_name, api_key, base_prompt, temperature)

        self.chat_model:BaseChatModel = init_chat_model("google_genai:" + model_name, api_key=api_key, temperature=temperature)
        
        # vincula tools de issues do GitHub ao modelo
        try:
            self.chat_model = self.chat_model.bind_tools(get_github_issue_tools())
        except Exception:
            # fallback: modelo nao suporta tools
            pass

    def generate_response(self, input: str) -> str:
        full_input = self.base_prompt + "\n" + input
        response = self.chat_model.invoke(full_input)
        
        if hasattr(response, 'tool_calls') and response.tool_calls:
            return self._handle_tool_calls(response, full_input)
        
        self.output = response.content
        return self.output
    
    def generate_response_with_prompt(self,  prompt: str, input: str) -> str:
        full_input = prompt + "\n" + input
        response = self.chat_model.invoke(full_input)
        
        if hasattr(response, 'tool_calls') and response.tool_calls:
            return self._handle_tool_calls(response, full_input)
        
        self.output = response.content
        return self.output
    
    def _handle_tool_calls(self, response, original_input: str) -> str:
        from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
        
        messages = [
            HumanMessage(content=original_input),
            response
        ]
        
        for tool_call in response.tool_calls:
            tool_name = tool_call['name']
            tool_args = tool_call['args']
            
            tools = {t.name: t for t in get_github_issue_tools()}
            if tool_name in tools:
                tool_result = tools[tool_name].invoke(tool_args)
                messages.append(
                    ToolMessage(
                        content=str(tool_result),
                        tool_call_id=tool_call['id']
                    )
                )
        
        final_response = self.chat_model.invoke(messages)
        self.output = final_response.content
        return self.output
    
    def _count_tokens(self, input: str) -> int:
        return self.chat_model.get_num_tokens(
         self.base_prompt + "\n" + input
        )

class GPTAgent(AIAgent):
    def __init__(self, model_name: str, api_key: str, base_prompt: str, temperature: float = 0.2):
        api_key = api_key or os.environ.get("OPENAI_API_KEY")
        super().__init__(model_name, api_key, base_prompt, temperature)
        self.chat_model: BaseChatModel = init_chat_model("openai:" + model_name, api_key=api_key)
        
        try:
            self.chat_model = self.chat_model.bind_tools(get_github_issue_tools())
        except Exception:
            # fallback: modelo nao suporta tools
            pass

    def generate_response(self, input: str) -> str:
        full_input = self.base_prompt + "\n" + input
        parameters = {
            "model": self.model_name,
            "input": full_input,
        }
        if not self.model_name.startswith("gpt-5") or self.model_name.startswith("o"):
            parameters["temperature"] = self.temperature
        response = self.chat_model.invoke(**parameters)
        
        if hasattr(response, 'tool_calls') and response.tool_calls:
            return self._handle_tool_calls_gpt(response, full_input)
        
        self.output = response.content
        return self.output

    def generate_response_with_prompt(self, prompt: str, input: str) -> str:
        full_input = prompt + "\n" + input
        parameters = {
            "model": self.model_name,
            "input": full_input,
        }
        if not self.model_name.startswith("gpt-5") or self.model_name.startswith("o"):
            parameters["temperature"] = self.temperature
        response = self.chat_model.invoke(**parameters)
        
        if hasattr(response, 'tool_calls') and response.tool_calls:
            return self._handle_tool_calls_gpt(response, full_input)
        
        self.output = response.content
        return self.output
    
    def _handle_tool_calls_gpt(self, response, original_input: str) -> str:
        from langchain_core.messages import HumanMessage, ToolMessage
        
        messages = [
            HumanMessage(content=original_input),
            response
        ]
        
        for tool_call in response.tool_calls:
            tool_name = tool_call['name']
            tool_args = tool_call['args']
            
            tools = {t.name: t for t in get_github_issue_tools()}
            if tool_name in tools:
                tool_result = tools[tool_name].invoke(tool_args)
                messages.append(
                    ToolMessage(
                        content=str(tool_result),
                        tool_call_id=tool_call['id']
                    )
                )

        final_response = self.chat_model.invoke(messages)
        self.output = final_response.content
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