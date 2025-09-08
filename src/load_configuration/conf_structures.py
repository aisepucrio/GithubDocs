from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class LLMParameters:
    temperature: float
    max_tokens: int

@dataclass
class LLMConfiguration:
    name: str
    model: str
    api_key: str
    parameters: LLMParameters

@dataclass
class LLMProvider:
    family: str
    configurations: List[LLMConfiguration]

@dataclass
class LLM:
    providers: List[LLMProvider]
    default_provider: str

@dataclass
class TargetInformation:
    repo_path: str
    branch_name: str
    dependency_file_path: str
    programing_language: str
    expected_result_type: str
    start_date: str = ""
    end_date: str = ""
    description: str = ""
    framework: str = "none"

@dataclass
class ExtractInformation:
    types: List[str]

@dataclass
class AgentComponent:
    name: str
    description: str
    prompt: str
    model_name: str

@dataclass
class Agents:
    components: List[AgentComponent]

@dataclass
class OrchestrationFlowStep:
    step: int
    from_step: str 
    to: str
    extract_information_types: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(
            step=data["step"],
            from_step=data["from"],
            to=data["to"],
            extract_information_types=data.get("extract_information_types")
        )

@dataclass
class Orchestration:
    max_retries: int
    timeout_seconds: int
    flow: List[OrchestrationFlowStep]

@dataclass
class OutputFile:
    name: str
    format: str

@dataclass
class OutputComponent:
    name: str
    path: str
    template: str
    file: OutputFile

@dataclass
class Output:
    components: List[OutputComponent]


@dataclass
class Evaluation:
    method: str
    objective_file_path: str

@dataclass
class FrameworkConfig:
    target_information: TargetInformation
    extract_information: ExtractInformation
    llm: LLM
    agents: Agents
    orchestration: Orchestration
    output: Output
    evaluation: Evaluation