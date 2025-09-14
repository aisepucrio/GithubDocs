from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class TargetInformation:
    repo_path: str
    branch_name: str
    start_date: str
    end_date: str
    dependency_file_path: str
    description: str
    framework: str
    programing_language: str
    expected_result_type: str

@dataclass
class OrchestrationFlowStep:
    step: int
    from_step: str
    extract_information_types: str

@dataclass
class Orchestration:
    max_retries: int
    timeout_seconds: int
    flow: List[OrchestrationFlowStep]

@dataclass
class Evaluation:
    method: str
    objective_file_path: str

@dataclass
class LLMProvider:
    family: str
    api_key: str
    name: str
    model: str
    temperature: float
    max_tokens: int

@dataclass
class LLM:
    providers: Dict[str, LLMProvider]
    default_provider: str

@dataclass
class AgentComponent:
    name: str
    description: str
    prompt: str
    model_name: str

@dataclass
class Agents:
    components: Dict[str, AgentComponent]

@dataclass
class Output:
    name: str
    path: str
    template: str
    file_name: str
    file_format: str
@dataclass
class FrameworkConfig:
    target_information: TargetInformation
    llm: LLM
    agents: Agents
    orchestration: Orchestration
    output: Output
    evaluation: Evaluation