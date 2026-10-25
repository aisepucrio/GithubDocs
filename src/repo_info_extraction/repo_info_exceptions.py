class RepoInfoExtractionError(Exception):
    """Base class for exceptions raised by the RepoInfoExtractor."""
    def __init__(self: str):
        super().__init__()
        self.message = """An error occurred during repository information extraction,
        this could happen due to library errors or invalid inputs not being handled.
        Please, check the repository path, branch name, and commit hashes provided.
        If the problem persists, consider opening an issue on the project's GitHub repository."""

    def __str__(self: str):
        return self.message


class ReadmeNotFoundError(RepoInfoExtractionError):
    """Raised when no README file is found in the repository."""
    def __init__(self: str):
        super().__init__()
        self.message = """No README file found in the repository.
        Please ensure that a README file (e.g., README.md, README.txt) exists in the root directory of the repository.
        If a README file exists, make sure it is committed to the repository.
        """


class InvalidRepositoryPathError(RepoInfoExtractionError):
    """Raised when the repository path is invalid."""
    def __init__(self: str):
        super().__init__()
        self.message = """Invalid repository path provided. Please ensure the path points to a valid Git repository.
        This could be cause by a non initialized submodule repository or a wrong path.
        submodules resolution:
        1. Navigate to the main repository directory.
        2. Run 'git submodule init' to initialize the submodules.
        3. Run 'git submodule update' to fetch the submodule content.
        wrong path:
        1. Double-check the path for typos or mistakes.
        2. Try to use Ctrl+click on the path in your IDE to verify if it exists.
        """

class InvalidBranchError(RepoInfoExtractionError):
    """Raised when the target branch is invalid."""
    def __init__(self: str):
        super().__init__()
        self.message = """Invalid branch name provided. Please ensure the branch exists in the repository.
        This could be caused by a typo in the branch name or by trying to access a branch that has been deleted.
        Branch resolution:
        1. Remove origin/ prefix if present in the branch name.
        2. Check the list of branches in the repository.
        3. Verify the branch name for typos or mistakes.
        4. If the branch has been deleted, consider checking out a different branch.
        """

class InvalidCommitError(RepoInfoExtractionError):
    """Raised when a commit is invalid."""
    def __init__(self, commit_hash: str = None):
        super().__init__()
        commit_reference = f"commit {commit_hash}" if commit_hash else "commit list"
        self.message = f"""Invalid {commit_reference} provided. Please ensure the commit(s) exist in the repository.
        This could be caused by an empty commit list, a typo in the commit hash, or by trying to access a commit that does not belong to the target branch.
        Commit resolution:
        1. Ensure that you provided at least one commit in commit_list.
        2. Ensure that you are in the right branch.
        3. Check the commit hash for typos or mistakes.
        """