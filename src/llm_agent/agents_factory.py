from ..load_configuration.conf_structures import AgentComponent, LLMProvider
from .agents_strategy import GeminiAgent, GPTAgent, AIAgent
#TODO: aqui fica meio foda, ja que o acoplamento entre agente e LLM é gigantesco, deve-se ver uma forma melhor
# de colocar as configurações da LLM em um dicionario em que o nome é a chave primária
# e o valor é um dicionario com as configurações, assim o agente pode pegar as configurações que quiser
# sem precisar de um acoplamento tão grande
def agent_factory(agent_config: AgentComponent, llm_provider: LLMProvider) -> AIAgent:

    family = agent_config.model_name

    if llm_provider.family == "gemini":
        return GeminiAgent(
            model_name=agent_config.model_name,
            api_key=llm_provider.api_key,
            base_prompt=agent_config.prompt
        )
    elif llm_provider.family == "openai":
        return GPTAgent(
            model_name=agent_config.model_name,
            api_key=llm_provider.api_key,
            base_prompt=agent_config.prompt
        )
    else:
        raise ValueError(f"Unsupported agent family: {llm_provider.family}")