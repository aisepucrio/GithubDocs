from dataclasses import dataclass
from pydantic import BaseModel
class Target_info(BaseModel):
    repo_path: str
    branch_name: str
    start_commit: str
    end_commit: str

    def __str__(self):
        return f"Target_info(repo_path={self.repo_path}, branch_name={self.branch_name}, start_commit={self.start_commit}, end_commit={self.end_commit})"


class Output_info(BaseModel):
    result_path: str
    log_path: str
    result_file_name: str

    def __str__(self):
        return f"Output_info(result_path={self.result_path}, log_path={self.log_path}, result_file_name={self.result_file_name})"


class Orchestration_step(BaseModel):
    step: int
    model_name: str
    temperature: float
    prompt_file: str
    extract_information_types: list[str]
    prompt_variables: dict[str, str]
    prompt: str = ""
    
    def __str__(self):
        return f"Orchestration_step(step={self.step}, model_name={self.model_name}, temperature={self.temperature}, prompt_path={self.prompt_path}, extract_information_types={self.extract_information_types}, prompt_variables={self.prompt_variables}, prompt={self.prompt[:50]}...)"
    
class BaseAppConfig(BaseModel):
    target_info: Target_info
    output_info: Output_info
    orchestration_steps: list[Orchestration_step]