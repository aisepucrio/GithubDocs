import tomli as tomllib
from pathlib import Path
from conf_structures import Target_info, Output_info, Orchestration_step, BaseAppConfig
from jinja2 import Environment, FileSystemLoader
import os


def read_config_file(file_path: str) -> dict[str, any]:
    with open(file_path, "rb") as f:
        config = tomllib.load(f)
    return config

def render_prompt(template_path: str, prompt_file: str, variables: dict) -> str:
    env = Environment(loader=FileSystemLoader(template_path))
    template = env.get_template(prompt_file)
    return template.render(variables)

def load_config(file_path: str) -> BaseAppConfig:
    config = read_config_file(file_path)

    target_info = Target_info.model_validate(config["target_information"])
    output_info = Output_info.model_validate(config["agents"]["output"][0])

    orchestration_steps = []

    # this for generate the prompt with jinja2
    for step in config["agents"]["orchestration"]:
        orch = Orchestration_step.model_validate(step)
        prompt =  orch.prompt_file
        try:
            step['prompt'] = render_prompt(target_info.template_path, prompt, step['prompt_variables'])
        except KeyError as e:
            print(f"\u274C Missing key in orchestration step {step['step']}:\n {e}")
            exit(1)
        except Exception as e:
            print(f"\u274C Error rendering prompt for step {step['step']}:\n {e}")
            exit(1)
    
        orchestration_steps.append(Orchestration_step.model_validate(step))
    
    sorted_steps = sorted(orchestration_steps, key=lambda x: x.step)

    return BaseAppConfig(
        target_info=target_info,
        output_info=output_info,
        orchestration_steps=sorted_steps
    )

# if __name__ == "__main__":
#     try:
#         config_data = load_config("conf/config.toml")
#         print("oi")
#         print(config_data)
#     except Exception as e:
#         print(f"\u274C Error loading config: {e}")
#         exit(1)