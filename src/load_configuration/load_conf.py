import tomli as tomllib
from pathlib import Path
from .conf_structures import TargetInfo, OutputInfo, OrchestrationStep, BaseAppConfig
from jinja2 import Environment, FileSystemLoader
import os
import re
from typing import Any


def expand_env_vars(value):
    if isinstance(value, str):
        pattern = r'\$\{([^}]+)\}'
        matches = re.findall(pattern, value)
        for var_name in matches:
            env_value = os.getenv(var_name, '')
            value = value.replace(f'${{{var_name}}}', env_value)
        pattern = r'\$([A-Z_][A-Z0-9_]*)'
        matches = re.findall(pattern, value)
        for var_name in matches:
            env_value = os.getenv(var_name, '')
            value = value.replace(f'${var_name}', env_value)
    elif isinstance(value, dict):
        return {k: expand_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [expand_env_vars(item) for item in value]
    return value


def read_config_file(file_path: str) -> dict[str, object]:
    with open(file_path, "rb") as f:
        config = tomllib.load(f)
        return expand_env_vars(config)

def load_config(file_path: str) -> BaseAppConfig:
    config = read_config_file(file_path)


    target_info = TargetInfo.model_validate(config["target_information"])
    output_info = OutputInfo.model_validate(config["agents"]["output"][0])

    orchestration_steps = []

    for step in config["agents"]["orchestration"]:
        orchestration_steps.append(OrchestrationStep.model_validate(step))
    
    sorted_steps = sorted(orchestration_steps, key=lambda x: x.step)

    return BaseAppConfig(
        target_info=target_info,
        output_info=output_info,
        orchestration_steps=sorted_steps
    )