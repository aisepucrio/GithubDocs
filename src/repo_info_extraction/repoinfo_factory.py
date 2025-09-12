from typing import Dict, Any, List
from .repoinfo_strategy import RepoInfo
from ..load_configuration.conf_structures import ExtractInformation, TargetInformation

def repo_info_factory(repo_path, branch,info) -> Dict[str, Any]:
    repo = RepoInfo(repo_path=repo_path,branch=branch)

    if info == "diff":
        return repo.getDiffs()
    elif info == "commits":
        return repo.getCommits()
    elif info == "readme":
        return repo.getReadMe()

def get_repoinfo_dictionary(target: TargetInformation, info: ExtractInformation) -> Dict[str, str]:
    repoinfo_dict = {}

    for info_type in info.components.items():
        repoinfo_dict[info_type] = repo_info_factory(target,info_type)
    return repoinfo_dict
