import tomli as tomllib
from conf_structures import Target_info, Output_info, Orchestration_step
from jinja2 import Environment, FileSystemLoader
import os

def read_config_file(file_path):
    with open(file_path, "rb") as f:
        config = tomllib.load(f)
    return config

def render_prompt(template_path, variables):
    env = Environment(loader=FileSystemLoader(os.getcwd() + '/prompt/'))
    template = env.get_template(template_path)
    return template.render(variables)

def load_config(file_path):
    config = read_config_file(file_path)

    target_info = Target_info(
        repo_path=config["target_information"]["repo_path"],
        branch_name=config["target_information"]["branch_name"],
        start_commit=config["target_information"]["start_commit"],
        end_commit=config["target_information"]["end_commit"]
    )

    output_info = Output_info(
        result_path=config["agents"]["output"][0]["result_path"],
        log_path=config["agents"]["output"][0]["log_path"],
        result_file_name=config["agents"]["output"][0]["result_file_name"]
    )

    orchestration_steps = [
        Orchestration_step(
            step=step["step"],
            model_name=step["model_name"],
            temperature=step["temperature"],
            prompt_path=step["prompt_file"],
            extract_information_types=step["extract_information_types"],
            prompt_variables=step["prompt_variables"],
            prompt=render_prompt(step["prompt_file"], step["prompt_variables"])
        ) for step in config["agents"]["orchestration"]
    ]

    return {
        "target_information": target_info,
        "output_information": output_info,
        "orchestration_steps": orchestration_steps
    }

if __name__ == "__main__":
    config_data = load_config("conf/config.toml")
    print(config_data)