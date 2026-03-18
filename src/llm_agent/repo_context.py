from typing import List, Optional

_IGNORED_FILES: set[str] = set()


def set_ignored_files(files: Optional[List[str]] = None):
    global _IGNORED_FILES
    _IGNORED_FILES = set(files or [])


def get_ignored_files() -> set[str]:
    return _IGNORED_FILES