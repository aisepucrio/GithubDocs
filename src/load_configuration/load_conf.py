import tomli as tomllib
from conf_structures import Target_info, Output_info, Orchestration_step, BaseAppConfig
from jinja2 import Environment, FileSystemLoader
import os
from pydantic import BaseModel

def read_config_file(file_path: str) -> dict[str, any]:
    with open(file_path, "rb") as f:
        config = tomllib.load(f)
    return config

def render_prompt(template_path: str, variables: dict) -> str:
    env = Environment(loader=FileSystemLoader(os.getcwd() + '/prompt/'))
    template = env.get_template(template_path)
    return template.render(variables)

def load_config(file_path: str) -> BaseAppConfig:
    config = read_config_file(file_path)

    target_info = Target_info.model_validate(config["target_information"])
    output_info = Output_info.model_validate(config["agents"]["output"][0])

    orchestration_steps = []

    # this for generate the prompt with jinja2
    for step in config["agents"]["orchestration"]:
        Orchestration_step.model_validate(step)
        try:
            step['prompt'] = render_prompt(step['prompt_file'], step['prompt_variables'])
        except KeyError as e:
            print(f"Missing key in orchestration step: {e}")
            raise e
        except Exception as e:
            print(f"Error rendering prompt for step")
            raise e
        orchestration_steps.append(Orchestration_step.model_validate(step))

    return BaseAppConfig(
        target_info=target_info,
        output_info=output_info,
        orchestration_steps=orchestration_steps
    )

if __name__ == "__main__":
    config_data = load_config("conf/config.toml")
    print(config_data)