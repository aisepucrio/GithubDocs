from src.load_configuration import read_configuration, sort_flow_steps
from src.load_configuration import FrameworkConfig
from src.llm_agent import AIAgent, get_agent_dictionary
from src.repo_info_extraction import get_repo_info
from src.load_configuration.conf_structures import OrchestrationFlowStep, Output
from typing import List, Dict
from dotenv import load_dotenv
import os

def build_repo_input(repo_information: Dict[str, str], input_type: str) -> str:
    types = [t.strip() for t in input_type.strip().split(",")]
    print("types", types)
    result = []
    for t in types:
        value = repo_information.get(t, "")
        if isinstance(value, list):
            result.extend(str(item) for item in value)
        else:
            result.append(str(value))
    return " ".join(result)

def generate_final_answer(orchestration_steps: List[OrchestrationFlowStep], agents: Dict[str, AIAgent], repo_information: Dict[str, str], output_info: Output) -> None:
    previous_response = ""
    for step in orchestration_steps:
        agent = agents.get(step.from_step)
        if agent:
            repo_input = build_repo_input(repo_information, step.extract_information_types)
            #print("repo_input", repo_input[:200])
            response = agent.generate_response(repo_input + previous_response)
            previous_response = ""
            #print(f"Response from {step.from_step}:\n{response[:100]}\n")
            if step.from_step == "output":
                with open(output_info.path + output_info.file_name + output_info.file_format, "w", encoding="utf-8") as f:
                    f.write(response)

            previous_response = response
        else:
            print(f"Agent {step.from_step} not found.")

def main_loop():
    load_dotenv()
    frame_conf = read_configuration("conf/config.yaml")
    llm_config = frame_conf.llm
    agents_conf = frame_conf.agents
    orchestration = frame_conf.orchestration
    output_info = frame_conf.output
    target_information_conf = frame_conf.target_information
    orchestration_steps = orchestration.flow

    repo_info_dict = get_repo_info(target_information_conf)
    agents = get_agent_dictionary(agents_conf, llm_config, output_info)

    generate_final_answer(orchestration_steps, agents, repo_info_dict, output_info)







