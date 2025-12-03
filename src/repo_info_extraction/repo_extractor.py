from pydriller import Repository
from git import Repo
from typing import Tuple
from identify import identify
from collections import Counter
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

    def __init__(self, repository_path: str, start_commit: str = None, end_commit: str = None, ignored_files: list[str] = None, target_branch: str = 'main'):
        self.repository_path = repository_path
        self.start_commit = start_commit
        self.end_commit = end_commit
        self.target_branch = target_branch
        self.ignored_files = ignored_files or []

        self.start_commit_date = None
        self.end_commit_date = None
        self.repo: Repository = self.get_repository()
        self.readme_text = self.get_readme_text()
        self.file_tree = self.get_file_tree()
        self.license = self.get_license()
        self.extensions = self.get_extensions()
    
    def get_readme_text(self) -> str:
        repo = Repo(self.repository_path)
        commit = repo.commit(self.end_commit) if self.end_commit else repo.head.commit
        
        readme_blob = None
        for item in commit.tree.traverse():
            if getattr(item, "type", None) == "blob" and getattr(item, "name", "").lower().startswith("readme"):
                readme_blob = item
                break

        if not readme_blob:
            raise ReadmeNotFoundError()

        return readme_blob.data_stream.read().decode("utf-8", errors="replace")
    
    def get_file_tree(self) -> str:
        repo = Repo(self.repository_path)
        file_tree = []
        excluded_defaults = {'.git', '__pycache__', 'node_modules', '.venv', 'venv'}
        excluded = excluded_defaults.union({s.strip() for s in self.ignored_files})

        for item in repo.tree().traverse():
            if any(excluded_dir in item.path.split('/') for excluded_dir in excluded):
                continue
            file_tree.append(item.path)

        return "\n".join(sorted(file_tree))


    def validate_branch(self, repo: Repo) -> bool:
        branches = [branch.name.replace('origin/', '', 1) if branch.name.startswith('origin/') else branch.name for branch in repo.remote().refs]
        return self.target_branch in branches

    def validate_commit(self, commit_hash: str, repo: Repo) -> bool:
        commits = [commit.hexsha for commit in repo.iter_commits()]
        return commit_hash in commits

    def validate_repository(self) -> Tuple[bool, Repo]:
        try:
            repo = Repo(self.repository_path)
            return (True, repo)
        except Exception:
            return (False, None)
        
    def get_repository(self) -> Repository:
        is_valid, repo = self.validate_repository()

        if not is_valid:
            raise InvalidRepositoryPathError()
        if not self.validate_branch(repo):
            raise InvalidBranchError()

        repo.git.checkout(self.target_branch)
        repo.remote().pull()
        repo.git.submodule('update', '--init', '--recursive')
        
        if self.start_commit and not self.validate_commit(self.start_commit, repo):
            raise InvalidCommitError(self.start_commit)
        if self.end_commit and not self.validate_commit(self.end_commit, repo):
            raise InvalidCommitError(self.end_commit)

        self.start_commit_date = self.start_commit and repo.commit(self.start_commit).committed_datetime
        self.end_commit_date = self.end_commit and repo.commit(self.end_commit).committed_datetime

        return Repository(self.repository_path,
                            since=self.start_commit_date,
                            to=self.end_commit_date,
                            only_in_branch=self.target_branch)

    def extract_repo_info(self) -> list[dict]:
        commit_result = []
        for commit in self.repo.traverse_commits():
            modified_files = commit.modified_files
            commit_info = {
                "hash": commit.hash,
                "date": commit.author_date,
                "message": commit.msg,
                "modifications":{}
            }
            for idx, modified_file in enumerate(modified_files):

                if modified_file.new_path in self.ignored_files:
                    continue

                key = f"{modified_file.new_path}_{idx}"
                commit_info["modifications"][key] = {
                    "change_type": modified_file.change_type.name,
                    "added_lines": modified_file.added_lines,
                    "diff": modified_file.diff,
                    "source_code_before": modified_file.source_code_before
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
    
    def get_license(self)-> str:
        license_file_path = f"{self.repository_path}/LICENSE"

        license = identify.license_id(license_file_path)

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
        print(e)