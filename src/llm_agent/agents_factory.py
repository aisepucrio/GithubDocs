from ..load_configuration.conf_structures import AgentComponent, LLMProvider, Agents, LLM
from .agents_strategy import GeminiAgent, GPTAgent, AIAgent
from typing import Dict

def agent_factory(agent_config: AgentComponent, llm_provider: Dict[str, LLMProvider]) -> AIAgent:

    family = llm_provider[agent_config.model_name].family
    if family == "gemini":
        return GeminiAgent(
            model_name=agent_config.model_name,
            api_key=llm_provider[agent_config.model_name].api_key,
            base_prompt=agent_config.prompt
        )
    elif family == "openai":
        return GPTAgent(
            model_name=agent_config.model_name,
            api_key=llm_provider[agent_config.model_name].api_key,
            base_prompt=agent_config.prompt
        )
    else:
        raise ValueError(f"Unsupported agent family: {family}")


def get_agent_dictionary(agents: Agents, llms: LLM) -> Dict[str, AIAgent]:
    agents_dict = {}

    for agent_name, agent_conf in agents.components.items():
        agents_dict[agent_name] = agent_factory(agent_conf, llms.providers)
    return agents_dict