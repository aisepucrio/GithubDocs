import re
import git
import os
from pathlib import Path
from util import solve_path_name

def commit_validator(commit: str) -> bool:
    """Validate that a commit hash is a valid SHA-1 hash."""

    sha1_regex = re.compile(r"^[a-fA-F0-9]{40}$")
    return bool(sha1_regex.match(commit)) or commit == "HEAD"

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
    
def temperature_validator(temperature: float) -> bool:
    """Validate that the temperature is between 0.0 and 2.0."""
    return 0.0 <= temperature <= 2.0

def path_validator(path: str) -> bool:
    """Validate that the output path is a valid directory."""
    path = solve_path_name(path)
    return os.path.isdir(path)

def extract_information_types_validator(types: list[str], allowed_types: list[str]) -> bool:
    """Validate that all extract information types are in the list of allowed types."""
    return all(t in allowed_types for t in types)