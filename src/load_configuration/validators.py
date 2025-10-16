import re
import git

def commit_validator(commit: str) -> bool:
    """Validate that a commit hash is a valid SHA-1 hash."""

    sha1_regex = re.compile(r"^[a-fA-F0-9]{40}$")
    return bool(sha1_regex.match(commit))

def repo_path_validator(repo_path: str) -> bool:
    """Validate that a repository path is a valid git repository."""
    try:
        _ = git.Repo(repo_path)
        return True
    except git.exc.InvalidGitRepositoryError:
        return False
    except git.exc.NoSuchPathError:
        return False