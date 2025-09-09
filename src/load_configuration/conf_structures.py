from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

class BaseConfig:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def __str__(self):
        return f"{self.__class__.__name__}(" + ", ".join(f"{k}={v}" for k, v in self.__dict__.items()) + ")"

class LLMProvider(BaseConfig):
    family: str
    api_key: str
    name: str
    model: str
    temperature: float
    max_tokens: int

class LLM(BaseConfig):
    providers: List[LLMProvider]
    default_provider: str

class TargetInformation(BaseConfig):
    repo_path: str
    branch_name: str
    dependency_file_path: str
    programing_language: str
    expected_result_type: str
    start_date: str = ""
    end_date: str = ""
    description: str = ""
    framework: str = "none"

class ExtractInformation(BaseConfig):
    types: List[str]

class AgentComponent(BaseConfig):
    name: str
    description: str
    prompt: str
    model_name: str

class Agents(BaseConfig):
    components: List[AgentComponent]

class OrchestrationFlowStep(BaseConfig):
    step: int
    from_step: str 
    to: str
    extract_information_types: Optional[str] = "all"    

class Orchestration(BaseConfig):
    max_retries: int
    timeout_seconds: int
    flow: List[OrchestrationFlowStep]
    

class OutputComponent(BaseConfig):
    name: str
    path: str
    template: str
    file_name: str
    file_format: str

class Output(BaseConfig):
    components: List[OutputComponent]

class Evaluation(BaseConfig):
    method: str
    objective_file_path: str

class FrameworkConfig(BaseConfig):
    target_information: TargetInformation
    extract_information: ExtractInformation
    llm: LLM
    agents: Agents
    orchestration: Orchestration
    output: Output
    evaluation: Evaluation