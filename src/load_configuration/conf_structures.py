from dataclasses import dataclass
from pydantic import BaseModel, field_validator
from .validators import *
import os
class Target_info(BaseModel):
    repo_path: str
    branch_name: str
    start_commit: str
    end_commit: str
    template_path: str = ""

    @field_validator("start_commit", "end_commit")
    def validate_commit(cls, v):
        if not commit_validator(v):
            raise ValueError("\u274C Invalid commit hash")
        return v
    
    @field_validator("repo_path")
    def validate_repo_path(cls, v):
        if not repo_path_validator(v):
            raise ValueError("\u274C Invalid repository path")
        return v
    
    @field_validator("template_path")
    def validate_template_path(cls, v):
        if not path_validator(v):
            raise ValueError("\u274C Invalid template path")
        return v

    def __str__(self):
        return f"Target_info(repo_path={self.repo_path}, branch_name={self.branch_name}, start_commit={self.start_commit}, end_commit={self.end_commit})"


class Output_info(BaseModel):
    result_path: str
    log_path: str
    result_file_name: str

    @field_validator("result_path", "log_path")
    def validate_paths(cls, v):
        if not path_validator(v):
            raise ValueError(f"\u274C Path does not exist or is not a directory: {v}\nPlease read the documentation carefully to set up the output paths.\n")
        return v

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

    @field_validator("temperature")
    def validate_temperature(cls, v):
        if not temperature_validator(v):
            raise ValueError("\u274C Temperature must be between 0.0 and 2.0")
        return v
    
    @field_validator("extract_information_types")
    def validate_extract_information_types(cls, v):
        # In this validation is interesting desing a better communication between modules
        return True
    
    def __str__(self):
        return f"Orchestration_step(step={self.step}, model_name={self.model_name}, temperature={self.temperature}, prompt_path={self.prompt_path}, extract_information_types={self.extract_information_types}, prompt_variables={self.prompt_variables}, prompt={self.prompt[:50]}...)"
    
class BaseAppConfig(BaseModel):
    target_info: Target_info
    output_info: Output_info
    orchestration_steps: list[Orchestration_step]