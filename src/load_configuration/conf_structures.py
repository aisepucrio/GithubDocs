from dataclasses import dataclass
from pydantic import BaseModel, field_validator
from .validators import *
from typing import Optional
import os


class TargetInfo(BaseModel):
    repo_path: str
    branch_name: str
    commit_list: Optional[list[str]] = None
    ignore_files: Optional[list[str]] = None
    github_repo_name: Optional[str] = None
    
    @field_validator("repo_path")
    def validate_repo_path(cls, v):
        if not path_validator(v):
            raise KeyError(f"\u274C Invalid repository {v}path")
        return v

    def __str__(self):
        return f"Target_info(repo_path={self.repo_path}, branch_name={self.branch_name}, commit_list={self.commit_list}, ignore_files={self.ignore_files}, github_repo_name={self.github_repo_name})"


class OutputInfo(BaseModel):
    result_path: str
    log_path: str
    result_file_name: str

    @field_validator("result_path", "log_path")
    def validate_paths(cls, v):
        if not path_validator(v):
            raise KeyError(f"\u274C Path does not exist or is not a directory: {v} Please read the documentation carefully to set up the output paths")
        return v

    def __str__(self):
        return f"Output_info(result_path={self.result_path}, log_path={self.log_path}, result_file_name={self.result_file_name})"


class OrchestrationStep(BaseModel):
    step: int
    model_name: str
    temperature: float
    prompt_file: str
    template_path: str = ""
    prompt_variables: dict[str, str]
    prompt: str = ""

    @field_validator("temperature")
    def validate_temperature(cls, v):
        if not temperature_validator(v):
            raise KeyError(f"\u274C Temperature must be between 0.0and 2.0")
        return v
    
    @field_validator("template_path")
    def validate_template_path(cls, v):
        if not path_validator(v):
            raise KeyError(f"\u274C Invalid template{v}path")
        return v
    
    def __str__(self):
        return f"OrchestrationStep(step={self.step}, model_name={self.model_name}, temperature={self.temperature}, prompt_path={self.prompt_file}, prompt_variables={self.prompt_variables}, prompt={self.prompt[:50]}...)"
    
class BaseAppConfig(BaseModel):
    target_info: TargetInfo
    output_info: OutputInfo
    orchestration_steps: list[OrchestrationStep]