import tomli as tomllib
from pathlib import Path
from .conf_structures import TargetInfo, OutputInfo, OrchestrationStep, BaseAppConfig
from jinja2 import Environment, FileSystemLoader
import os
from typing import Any


def read_config_file(file_path: str) -> dict[str, object]:
    with open(file_path, "rb") as f:
        return tomllib.load(f)

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