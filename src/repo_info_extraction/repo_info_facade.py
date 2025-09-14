from src.load_configuration.conf_structures import *
from .repo_info import GitManager

def get_repo_info(target_information: TargetInformation) -> dict:
    git_manager = GitManager()
    repo_info = {}

    if target_information.repo_path:
        repo_path = target_information.repo_path
        branch = target_information.branch_name or "main"
        start_date = target_information.start_date or None
        end_date = target_information.end_date or None
        
        git_manager.checkout_branch(repo_path, branch)
        git_manager.git_pull(repo_path, branch)
        
        repo_info = git_manager.get_dict_of_repo_info(repo_path, branch, start_date, end_date)

    return repo_info
