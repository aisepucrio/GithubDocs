from dataclasses import dataclass

@dataclass
class Target_info:
    repo_path: str
    branch_name: str
    start_commit: str
    end_commit: str

    def __str__(self):
        return f"Target_info(repo_path={self.repo_path}, branch_name={self.branch_name}, start_commit={self.start_commit}, end_commit={self.end_commit})"

@dataclass
class Output_info:
    result_path: str
    log_path: str
    result_file_name: str

    def __str__(self):
        return f"Output_info(result_path={self.result_path}, log_path={self.log_path}, result_file_name={self.result_file_name})"

@dataclass
class Orchestration_step:
    step: int
    model_name: str
    temperature: float
    prompt_path: str
    extract_information_types: list[str]
    prompt_variables: dict[str, str]
    prompt: str = ""  # Add the prompt field
    
    def __str__(self):
        return f"Orchestration_step(step={self.step}, model_name={self.model_name}, temperature={self.temperature}, prompt_path={self.prompt_path}, extract_information_types={self.extract_information_types}, prompt_variables={self.prompt_variables}, prompt={self.prompt[:50]}...)"