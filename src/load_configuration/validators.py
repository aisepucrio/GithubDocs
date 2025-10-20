import re
import git
import os
from pathlib import Path
from util import solve_path_name

def commit_validator(commit: str) -> bool:
    """Validate that a commit hash is a valid SHA-1 hash."""

    sha1_regex = re.compile(r"^[a-fA-F0-9]{40}$")
    return bool(sha1_regex.match(commit))

def repo_path_validator(repo_path: str) -> bool:
    """Validate that a repository path is a valid git repository."""    
    repo_path = solve_path_name(repo_path)
    try:
        _ = git.Repo(repo_path)
        return True
    except git.InvalidGitRepositoryError:
        return False
    except git.NoSuchPathError:
        return False
    
def branch_name_validator(repo_path: str, branch_name: str) -> bool:
    """Validate that a branch name exists in the given git repository."""
    repo_path = solve_path_name(repo_path)
    try:
        repo = git.Repo(repo_path)
        return branch_name in [head.name for head in repo.heads]
    except git.InvalidGitRepositoryError:
        return False
    except git.NoSuchPathError:
        return False
    
def temperature_validator(temperature: float) -> bool:
    """Validate that the temperature is between 0.0 and 2.0."""
    return 0.0 <= temperature <= 2.0

def output_path_validator(path: str) -> bool:
    """Validate that the output path is a valid directory."""
    return os.path.isdir(path)

def prompt_file_validator(file_path: str) -> bool:
    """Validate that the prompt file exists."""
    return (Path.cwd() / 'prompt' / file_path).is_file()

def extract_information_types_validator(types: list[str], allowed_types: list[str]) -> bool:
    """Validate that all extract information types are in the list of allowed types."""
    return all(t in allowed_types for t in types)