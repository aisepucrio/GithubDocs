# ...existing code...
import os
from pathlib import Path

class PathSolver:
    @staticmethod
    def solve_path(path: str) -> str:
        if not path:
            raise ValueError("path must not be empty")

        p = Path(path).expanduser()
        if not p.is_absolute():
            p = Path.cwd() / p

        p = p.resolve(strict=False)
        return str(p)
# ...existing code...