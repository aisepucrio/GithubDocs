from ..load_configuration.conf_structures import AgentComponent, LLMProvider, Agents, LLM, Output
from .agents_strategy import GeminiAgent, GPTAgent, AIAgent
from typing import Dict

def agent_factory(agent_config: AgentComponent, llm_provider: Dict[str, LLMProvider]) -> AIAgent:

    family = llm_provider[agent_config.model_name].family
    #print(llm_provider[agent_config.model_name].name)
    if family == "gemini":
        return GeminiAgent(
            model_name=llm_provider[agent_config.model_name].model,
            api_key=llm_provider[agent_config.model_name].api_key,
            base_prompt=agent_config.prompt
        )
    elif family == "openai":
        return GPTAgent(
            model_name=llm_provider[agent_config.model_name].model,
            api_key=llm_provider[agent_config.model_name].api_key,
            base_prompt=agent_config.prompt
        )
    else:
        raise ValueError(f"Unsupported agent family: {family}")

def agent_factory_out(output: Output, llm: LLM) -> AIAgent:
    family = llm.providers[llm.default_provider].family
    prompt = "Put the following text in a structured format according to the template: \n\n" + output.template
    if family == "gemini":
        return GeminiAgent(
            model_name=llm.providers[llm.default_provider].model,
            api_key=llm.providers[llm.default_provider].api_key,
            base_prompt=prompt
        )
    elif family == "openai":
        return GPTAgent(
            model_name=llm.providers[llm.default_provider].model,
            api_key=llm.providers[llm.default_provider].api_key,
            base_prompt=prompt
        )
    else:
        raise ValueError(f"Unsupported agent family: {family}")

def get_agent_dictionary(agents: Agents, llms: LLM, output: Output) -> Dict[str, AIAgent]:
    agents_dict = {}

    for agent_name, agent_conf in agents.components.items():
        agents_dict[agent_name] = agent_factory(agent_conf, llms.providers)

    agents_dict["output"] = agent_factory_out(output, llms)
    return agents_dict