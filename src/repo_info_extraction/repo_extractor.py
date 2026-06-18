from pydriller import Repository
from git import Repo
from identify import identify
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from functools import cached_property
import fnmatch
import os
import threading

from langchain_core.tools import StructuredTool

from .repo_info_exceptions import (
    RepoInfoExtractionError,
    InvalidRepositoryPathError,
    InvalidBranchError,
    InvalidCommitError,
)

EXCLUDED_TREE_DIRS = {'.git', '__pycache__', 'node_modules', '.venv', 'venv'}


@dataclass
class ModificationDetail:
    change_type: str
    added_lines: int
    diff: str | None
    source_code_before: str | None


@dataclass
class CommitSummary:
    hash: str
    date: datetime
    message: str


@dataclass
class CommitDetail:
    hash: str
    date: datetime
    message: str
    modifications: dict[str, ModificationDetail]


def repo_tool(method):
    """Marks a RepoInfoExtractor method to be exposed as an LLM tool via as_tools().

    The method's docstring becomes the tool description; its name becomes the tool name.
    Marked methods must accept only JSON-serializable arguments and return a string.
    """
    method._is_repo_tool = True
    return method


def _format_commit_summaries(summaries: list[CommitSummary]) -> str:
    if not summaries:
        return "No commits available."
    return "\n".join(
        f"{s.hash} | {s.date.isoformat()} | {s.message.splitlines()[0] if s.message else ''}"
        for s in summaries
    )


def _format_commit_detail(detail: CommitDetail) -> str:
    lines = [
        f"Commit: {detail.hash}",
        f"Date: {detail.date.isoformat()}",
        f"Message: {detail.message}",
        f"Modifications ({len(detail.modifications)}):",
    ]
    for key, mod in detail.modifications.items():
        lines.append(f"- {key} | {mod.change_type} | +{mod.added_lines}")
        if mod.diff:
            lines.append("  diff:")
            lines.append(mod.diff)
    return "\n".join(lines)


class RepoInfoExtractor:

    def __init__(self, repository_path: str, commit_list: list[str] = None,
                 ignored_files: list[str] = None, target_branch: str = 'main'):
        self.repository_path = repository_path
        self.commit_list = commit_list
        self.target_branch = target_branch
        self.ignored_files = ignored_files or []

        # Serializes git/pydriller access. langgraph's ToolNode runs tool calls
        # from a single turn in parallel threads; pydriller acquires a write lock
        # on the repo's git config on every Repository creation, so concurrent
        # tool calls would otherwise collide with "Lock ... already exists".
        self._git_lock = threading.RLock()

        self.git_repo: Repo = self._open_git_repo()
        self._validate_branch()
        self._stash_dirty_changes()
        self._resolved_commits: list[str] = self._resolve_commits()
        self.last_commit_hash: str = self._resolved_commits[-1]

        self._commit_summaries: list[CommitSummary] | None = None
        self._commit_detail_cache: dict[str, CommitDetail] = {}
        self._tools_cache: list | None = None

    # --------- setup / validation ---------

    def _open_git_repo(self) -> Repo:
        try:
            return Repo(self.repository_path)
        except Exception:
            raise InvalidRepositoryPathError()

    def _validate_branch(self) -> None:
        try:
            branches = [
                b.name.replace('origin/', '', 1) if b.name.startswith('origin/') else b.name
                for b in self.git_repo.remote().refs
            ]
        except Exception:
            raise InvalidBranchError()
        if self.target_branch not in branches:
            raise InvalidBranchError()

    def _stash_dirty_changes(self) -> None:
        if not self.git_repo.is_dirty(untracked_files=True):
            return
        try:
            self.git_repo.git.stash('push', '--include-untracked')
        except Exception:
            try:
                self.git_repo.git.stash('save', '--include-untracked')
            except Exception as e:
                raise RepoInfoExtractionError(f"Failed to stash local changes: {e}")

    def _resolve_commits(self) -> list[str]:
        commits: list[str] = []
        for commit_hash in self.commit_list or []:
            if ":" in commit_hash:
                start_commit, end_commit = commit_hash.split(":")
                try:
                    range_commits = [
                        c.hash for c in Repository(
                            self.repository_path,
                            from_commit=start_commit,
                            to_commit=end_commit,
                            only_in_branch=self.target_branch,
                        ).traverse_commits()
                    ]
                except Exception:
                    raise InvalidCommitError(commit_hash)
                if not range_commits:
                    raise InvalidCommitError(commit_hash)
                commits.extend(range_commits)
            else:
                found = list(Repository(
                    self.repository_path,
                    single=commit_hash,
                    only_in_branch=self.target_branch,
                ).traverse_commits())
                if not found:
                    raise InvalidCommitError(commit_hash)
                commits.append(commit_hash)

        if not commits:
            raise InvalidCommitError()

        return [
            c.hash for c in Repository(
                self.repository_path,
                only_commits=commits,
                only_in_branch=self.target_branch,
            ).traverse_commits()
        ]

    # --------- helpers ---------

    def _is_ignored(self, path: str) -> bool:
        for pattern in self.ignored_files:
            if fnmatch.fnmatch(path, pattern):
                return True
            if fnmatch.fnmatch(os.path.basename(path), pattern):
                return True
        return False

    def _iter_tracked_blobs(self):
        for item in self.git_repo.tree().traverse():
            parts = item.path.split('/')
            if any(p in EXCLUDED_TREE_DIRS for p in parts):
                continue
            yield item

    def _traverse_resolved_commits(self):
        return Repository(
            self.repository_path,
            only_commits=self._resolved_commits,
            only_in_branch=self.target_branch,
        ).traverse_commits()

    def _build_commit_detail(self, commit) -> CommitDetail:
        modifications: dict[str, ModificationDetail] = {}
        for idx, modified_file in enumerate(commit.modified_files):
            path_to_check = modified_file.new_path or modified_file.old_path
            if self._is_ignored(path_to_check):
                continue

            key = f"{modified_file.new_path}_{idx}"
            if 'binary' in identify.tags_from_filename(path_to_check):
                diff = None
                source_code_before = None
            else:
                try:
                    diff = modified_file.diff
                    source_code_before = modified_file.source_code_before
                except ValueError:
                    diff = None
                    source_code_before = None

            modifications[key] = ModificationDetail(
                change_type=modified_file.change_type.name,
                added_lines=modified_file.added_lines,
                diff=diff,
                source_code_before=source_code_before,
            )

        return CommitDetail(
            hash=commit.hash,
            date=commit.author_date,
            message=commit.msg,
            modifications=modifications,
        )

    # --------- raw cached data (Python/template use) ---------

    @cached_property
    def readme(self) -> str | None:
        with self._git_lock:
            commit = self.git_repo.commit(self.last_commit_hash)
            for item in commit.tree.traverse():
                is_blob = getattr(item, "type", None) == "blob"
                name = getattr(item, "name", "")
                if is_blob and name.lower().startswith("readme"):
                    return item.data_stream.read().decode("utf-8", errors="replace")
            return None

    @cached_property
    def file_tree(self) -> str:
        with self._git_lock:
            files = [
                item.path for item in self._iter_tracked_blobs()
                if not self._is_ignored(item.path)
            ]
        return "\n".join(sorted(files))

    @cached_property
    def license(self) -> str:
        try:
            license_file_path = os.path.join(self.repository_path, "LICENSE")
            license_id = identify.license_id(license_file_path)
            return license_id or "LICENSE exists, check License File"
        except Exception:
            return "No License File"

    @cached_property
    def extensions(self) -> str:
        ext_list = []
        with self._git_lock:
            for item in self._iter_tracked_blobs():
                if item.type != 'blob':
                    continue
                _, ext = os.path.splitext(item.path)
                ext = ext.lower()
                if ext:
                    ext_list.append(ext)

        counter = Counter(ext_list)
        total = sum(counter.values())
        if total == 0:
            return ""

        percentages = sorted(
            ((ext, round((count / total) * 100, 2)) for ext, count in counter.items()),
            key=lambda kv: kv[1],
            reverse=True,
        )
        return ", ".join(f"{ext}: {pct}%" for ext, pct in percentages[:5])

    def _list_commits_objs(self) -> list[CommitSummary]:
        if self._commit_summaries is None:
            with self._git_lock:
                if self._commit_summaries is None:
                    self._commit_summaries = [
                        CommitSummary(hash=c.hash, date=c.author_date, message=c.msg)
                        for c in self._traverse_resolved_commits()
                    ]
        return self._commit_summaries

    def _get_commit_detail_obj(self, commit_hash: str) -> CommitDetail:
        if commit_hash in self._commit_detail_cache:
            return self._commit_detail_cache[commit_hash]

        with self._git_lock:
            if commit_hash in self._commit_detail_cache:
                return self._commit_detail_cache[commit_hash]

            for c in Repository(
                self.repository_path,
                single=commit_hash,
                only_in_branch=self.target_branch,
            ).traverse_commits():
                detail = self._build_commit_detail(c)
                self._commit_detail_cache[commit_hash] = detail
                return detail

        raise InvalidCommitError(commit_hash)

    # --------- LLM tools (string-returning, exposed via as_tools) ---------

    @repo_tool
    def get_readme(self) -> str:
        """Returns the README content of the repository at the latest analyzed commit."""
        return self.readme or "No README found in the repository."

    @repo_tool
    def get_file_tree(self) -> str:
        """Returns the file tree of the repository as a newline-separated list of file paths."""
        return self.file_tree or "No files found."

    @repo_tool
    def get_license(self) -> str:
        """Returns the SPDX license identifier of the repository's LICENSE file, or a status message if missing."""
        return self.license

    @repo_tool
    def get_extensions(self) -> str:
        """Returns the top-5 file extensions in the repository with their percentage of occurrence."""
        return self.extensions or "No extensions detected."

    @repo_tool
    def list_commits(self) -> str:
        """Lists all commits being analyzed (one per line: hash | date | first message line). Call this to discover available commit hashes before requesting commit details."""
        return _format_commit_summaries(self._list_commits_objs())

    @repo_tool
    def get_commit_detail(self, commit_hash: str) -> str:
        """Returns full detail of a single commit (metadata + per-file modifications and diffs) for a given commit hash. Use list_commits first to discover valid hashes."""
        return _format_commit_detail(self._get_commit_detail_obj(commit_hash))

    # --------- tool factory ---------

    def as_tools(self) -> list:
        """Returns langchain StructuredTool wrappers for every method marked with @repo_tool.

        Bound methods are passed in, so `self` is already captured and does not appear in
        the tool's input schema — this is the langchain-friendly way to expose instance
        methods (see CLAUDE.md gotcha on @tool + instance methods).
        """
        if self._tools_cache is not None:
            return self._tools_cache

        tools = []
        for name, member in vars(type(self)).items():
            if not getattr(member, '_is_repo_tool', False):
                continue
            bound = getattr(self, name)
            tools.append(StructuredTool.from_function(
                func=bound,
                name=name,
                description=(member.__doc__ or "").strip(),
            ))
        self._tools_cache = tools
        return tools

    # --------- backward-compat dict view ---------

    def extract_repo_info(self) -> dict:
        commits = []
        summaries = []
        for c in self._traverse_resolved_commits():
            detail = self._build_commit_detail(c)
            self._commit_detail_cache[detail.hash] = detail
            summaries.append(CommitSummary(hash=detail.hash, date=detail.date, message=detail.message))
            commits.append({
                "hash": detail.hash,
                "date": detail.date,
                "message": detail.message,
                "modifications": {
                    key: {
                        "change_type": mod.change_type,
                        "added_lines": mod.added_lines,
                        "diff": mod.diff,
                        "source_code_before": mod.source_code_before,
                    }
                    for key, mod in detail.modifications.items()
                },
            })

        if self._commit_summaries is None:
            self._commit_summaries = summaries

        return {
            "repo_path": self.repository_path,
            "readme": self.readme,
            "file_tree": self.file_tree,
            "commits": commits,
            "license": self.license,
            "extensions": self.extensions,
        }
