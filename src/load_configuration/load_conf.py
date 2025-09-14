from .conf_structures import *
import yaml

def _read_configuration(file_path: str) -> dict:
    with open(file_path, 'r') as file:
        config = yaml.safe_load(file)
    return config

def sort_flow_steps(steps: List[dict]) -> List[dict]:
    return sorted(steps, key=lambda x: x['step'])

def read_configuration(file_path: str) -> FrameworkConfig:
    config = _read_configuration(file_path)

    target_information = TargetInformation(**config['target_information'])
    
    llm_providers = {
        provider['name']: LLMProvider(**provider) 
        for provider in config['llm']['providers']
    }
    llm = LLM(providers=llm_providers, default_provider=config['llm']['default_provider'])
    agent_components = {
        comp['name']: AgentComponent(**comp) 
        for comp in config['agents']['components']
    }
    agents = Agents(components=agent_components)

    flow_steps_data = config['orchestration']['flow']
    # Sort the dictionaries before converting to OrchestrationFlowStep objects
    sorted_flow_steps_data = sort_flow_steps(flow_steps_data)
    orchestration_flow = []
    for step_data in sorted_flow_steps_data:
        step_data['from_step'] = step_data.pop('from')
        orchestration_flow.append(OrchestrationFlowStep(**step_data))

    orchestration = Orchestration(
        max_retries=config['orchestration']['max_retries'],
        timeout_seconds=config['orchestration']['timeout_seconds'],
        flow=orchestration_flow
    )

    output = Output(**config['output'])

    evaluation = Evaluation(**config['evaluation'])

    framework_config = FrameworkConfig(
        target_information=target_information,
        llm=llm,
        agents=agents,
        orchestration=orchestration,
        output=output,
        evaluation=evaluation
    )

    return framework_config

if __name__ == "__main__":
    f = read_configuration("conf/config.yaml")
    print("--- Acesso ao Output Component 'changelog_output' ---")
    changelog_conf = f.output
    print(f"File Name: {changelog_conf.file_name}")
    print(f"File Format: {changelog_conf.file_format}\n")

    print("--- Acesso ao LLM Provider 'gpt4' ---")
    gpt4_conf = f.llm.providers['gpt4']
    print(f"Model: {gpt4_conf.model}")
    print(f"Temperature: {gpt4_conf.temperature}\n")

    print("--- Acesso ao Agent ---")
    first_agent_key = next(iter(f.agents.components))
    doc_store_agent = f.agents.components[first_agent_key]
    print(f"Description: {doc_store_agent.description}")

    print("--- Orchestration Steps ---")
    for step in f.orchestration.flow:
        print(f"Step: {step.step}, Name: {step.from_step}, Extract: {step.extract_information_types}")