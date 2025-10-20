from pathlib import Path

def solve_path_name(repo_path: str) -> str:
    if not repo_path:
        raise ValueError("repo_path must not be empty")

    p = Path(repo_path).expanduser()
    if not p.is_absolute():
        p = Path.cwd() / p

    p = p.resolve(strict=False)
    p = str(p)
    return p