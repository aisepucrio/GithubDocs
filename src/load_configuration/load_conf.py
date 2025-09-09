from conf_structures import *

def _read_configuration(file_path: str) -> dict:
    import yaml
    with open(file_path, 'r') as file:
        config = yaml.safe_load(file)
    return config

def read_configuration(file_path: str) -> FrameworkConfig:
    config = _read_configuration(file_path)

    target_information = TargetInformation(**config['target_information'])
    extract_information_types = ExtractInformation(**config['extract_information'])
    
    llm_providers = [LLMProvider(**provider) for provider in config['llm']['providers']]
    llm = LLM(providers=llm_providers, default_provider=config['llm']['default_provider'])

    agents = Agents(**config['agents'])

    orchestration_flow = [OrchestrationFlowStep(**step) for step in config['orchestration']['flow']]
    orchestration = Orchestration(
        max_retries=config['orchestration']['max_retries'],
        timeout_seconds=config['orchestration']['timeout_seconds'],
        flow=orchestration_flow
    )
    output_components = [OutputComponent(**component) for component in config['output']['components']]
    output = Output(components=output_components)

    evaluation = Evaluation(**config['evaluation'])

    framework_config = FrameworkConfig(
        target_information=target_information,
        extract_information=extract_information_types,
        llm=llm,
        agents=agents,
        orchestration=orchestration,
        output=output,
        evaluation=evaluation
    )

    return framework_config

if __name__ == "__main__":
    f = read_configuration("conf/config.yaml")
    print(f.output.components[0].file_name)
    print(f.output.components[0].file_format)
