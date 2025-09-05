
from dataclasses import dataclass

@dataclass
class LLMConfig:
    model: str
    api_key: str
    parameters: dict

@dataclass
class TargetConfig:
    repository_path: str
    type: str
    readme: dict
    changelog: dict


@dataclass
class EvaluationConfig:
    method: str
    objective_file_path: str