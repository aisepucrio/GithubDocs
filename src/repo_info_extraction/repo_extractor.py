from pydriller import Repository
from git import Repo
from typing import Tuple
from identify import identify
from collections import Counter
import fnmatch
import os

from .repo_info_exceptions import (
    RepoInfoExtractionError,
    InvalidRepositoryPathError,
    InvalidBranchError,
    InvalidCommitError,
    ReadmeNotFoundError
)

# TODO: Some parts of that code are redundant with the operations made by pydriller.
# After an initial version working, I suggest to refactor to use the pydriller errors or just use gitpython.

class RepoInfoExtractor:

    def __init__(self, repository_path: str, commit_list: list[str] = None, ignored_files: list[str] = None, target_branch: str = 'main'):
        self.repository_path = repository_path
        self.commit_list = commit_list
        self.target_branch = target_branch
        self.ignored_files = ignored_files or []
        self.last_commit_hash = None

        self.repo: Repository = self.get_repository()
        self.readme_text = self.get_readme_text()
        self.file_tree = self.get_file_tree()
        self.license = self.get_license()
        self.extensions = self.get_extensions()


    def get_readme_text(self) -> str:
        git_repo = Repo(self.repository_path)
        commit = git_repo.commit(self.last_commit_hash)

        readme_blob = None
        for item in commit.tree.traverse():
            if getattr(item, "type", None) == "blob" and getattr(item, "name", "").lower().startswith("readme"):
                readme_blob = item
                break

        if not readme_blob:
            return None
        return readme_blob.data_stream.read().decode("utf-8", errors="replace")

    def _is_ignored(self, path: str) -> bool:
        """Check if a path matches any of the ignore patterns (supports glob)."""
        for pattern in self.ignored_files:
            if fnmatch.fnmatch(path, pattern):
                return True
            # Also match against the basename for patterns like *.jpg
            if fnmatch.fnmatch(os.path.basename(path), pattern):
                return True
        return False

    def get_file_tree(self) -> str:
        repo = Repo(self.repository_path)
        file_tree = []
        excluded_defaults = {'.git', '__pycache__', 'node_modules', '.venv', 'venv'}

        for item in repo.tree().traverse():
            if any(excluded_dir in item.path.split('/') for excluded_dir in excluded_defaults):
                continue
            if self._is_ignored(item.path):
                continue
            file_tree.append(item.path)

        return "\n".join(sorted(file_tree))


    def validate_branch(self, repo: Repo) -> bool:
        branches = [branch.name.replace('origin/', '', 1) if branch.name.startswith('origin/') else branch.name for branch in repo.remote().refs]
        return self.target_branch in branches

    def validate_pydriller_branch(self, repo: Repository) -> bool:
        try:
            git_repo = self.validate_repository()[1]
            branches = [branch.name.replace('origin/', '', 1) if branch.name.startswith('origin/') else branch.name for branch in git_repo.remote().refs]
            return self.target_branch in branches
        except Exception:
            return False

    def validate_commit(self, commit_hash: str, repo: Repo) -> bool:
        commits = [commit.hexsha for commit in repo.iter_commits()]
        return commit_hash in commits

    def validate_repository(self) -> Tuple[bool, Repo]:
        try:
            repo = Repo(self.repository_path)
            return (True, repo)
        except Exception:
            return (False, None)

    def validate_pydriller_repository(self) -> Tuple[bool, Repository]:
        try:
            repo = Repository(path_to_repo=self.repository_path, only_in_branch=self.target_branch)
            return (True, repo)
        except Exception:
            return (False, None)

    def stash_changes(self, repo: Repository) -> None:
        try:
            git_repo = Repo(self.repository_path)
            if git_repo.is_dirty(untracked_files=True):
                try:
                    git_repo.git.stash('push', '--include-untracked')
                except Exception:
                    try:
                        git_repo.git.stash('save', '--include-untracked')
                    except Exception as e:
                        raise RepoInfoExtractionError(f"Failed to stash local changes: {e}")
        except RepoInfoExtractionError:
            raise
        except Exception as e:
            raise RepoInfoExtractionError(f"Failed to access repository for stashing: {e}")

    def get_repository(self) -> Repository:
        is_valid, repo = self.validate_pydriller_repository()

        if not is_valid:
            raise InvalidRepositoryPathError()

        is_valid = self.validate_pydriller_branch(repo)
        if not is_valid:
            raise InvalidBranchError()

        self.stash_changes(repo)

        commit_list = []

        for commit_hash in self.commit_list or []:
            if ":" in commit_hash:
                start_commit, end_commit = commit_hash.split(":")
                try:
                    range_commits = [
                        c.hash for c in Repository(
                            self.repository_path,
                            from_commit=start_commit,
                            to_commit=end_commit,
                            only_in_branch=self.target_branch
                        ).traverse_commits()
                    ]
                except Exception:
                    raise InvalidCommitError(commit_hash)
                if not range_commits:
                    raise InvalidCommitError(commit_hash)
                commit_list.extend(range_commits)
            else:
                found = list(Repository(
                    self.repository_path,
                    single=commit_hash,
                    only_in_branch=self.target_branch
                ).traverse_commits())
                if not found:
                    raise InvalidCommitError(commit_hash)
                commit_list.append(commit_hash)

        if not commit_list:
            raise InvalidCommitError()
        ordered = [
            c.hash for c in Repository(
                self.repository_path,
                only_commits=commit_list,
                only_in_branch=self.target_branch
            ).traverse_commits()
        ]
        self.last_commit_hash = ordered[-1]

        return Repository(self.repository_path,
                          only_commits=commit_list,
                          only_in_branch=self.target_branch)

    def extract_repo_info(self) -> list[dict]:
        commit_result = []
        for commit in self.repo.traverse_commits():
            modified_files = commit.modified_files
            commit_info = {
                "hash": commit.hash,
                "date": commit.author_date,
                "message": commit.msg,
                "modifications": {}
            }
            for idx, modified_file in enumerate(modified_files):
                # resolve o caso onde o commit deleta um file (new_path é None)
                path_to_check = modified_file.new_path or modified_file.old_path
                if self._is_ignored(path_to_check):
                    continue

                key = f"{modified_file.new_path}_{idx}"
                try:
                    diff = modified_file.diff
                    source_code_before = modified_file.source_code_before
                except ValueError:
                    diff = None
                    source_code_before = None
                commit_info["modifications"][key] = {
                    "change_type": modified_file.change_type.name,
                    "added_lines": modified_file.added_lines,
                    "diff": diff,
                    "source_code_before": source_code_before
                }
            commit_result.append(commit_info)
        return {
            "repo_path": self.repository_path,
            "readme": self.readme_text,
            "file_tree": self.file_tree,
            "commits": commit_result,
            "license": self.license,
            "extensions": self.extensions
        }


    def get_license(self) -> str:
        try:
            license_file_path = f"{self.repository_path}/LICENSE"
            license = identify.license_id(license_file_path)
            if license == None:
                license = "LICENSE exists, check License File"
            return license
        except Exception:
            license = "No License File"
            return license

    def get_extensions(self, extra_excluded: list[str] = None) -> str:
        repo = Repo(self.repository_path)

        excluded = {'.git', '__pycache__', 'node_modules', '.venv', 'venv'}

        if extra_excluded:
            excluded.update(extra_excluded)

        extensions = []

        for item in repo.tree().traverse():
            parts = item.path.split('/')
            if any(part in excluded for part in parts):
                continue

            if item.type == 'blob':
                _, ext = os.path.splitext(item.path)
                ext = ext.lower()
                if ext:
                    extensions.append(ext)

        counter = Counter(extensions)
        total = sum(counter.values())

        percentages = {
            ext: round((count / total) * 100, 2)
            for ext, count in counter.items()
        }

        percentages = {
            ext: pct for ext, pct in sorted(percentages.items(), key=lambda item: item[1], reverse=True)
        }

        top_5_extensions = dict(list(percentages.items())[:5])
        extensions_str = ", ".join([f"{k}: {v}%" for k, v in top_5_extensions.items()])

        return extensions_str


if __name__ == "__main__":

    start_commit = "b4a27b33d3f7a886fa0ca09d6221602d98b52053"
    end_commit = "51ad10771654b45e9f1470ae32928c09b411f5a0"

    start_commit, end_commit = end_commit, start_commit

    try:
        extractor = RepoInfoExtractor("/home/PUC/Documentos/GithubDocs/external_repos/EventFlow",
                                      start_commit=start_commit,
                                      end_commit=end_commit,
                                      target_branch="develop-v1")

        repo_info = extractor.extract_repo_info()
    except RepoInfoExtractionError as e:
        pass