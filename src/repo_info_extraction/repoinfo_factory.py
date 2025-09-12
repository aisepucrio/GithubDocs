from typing import Dict
from .repoinfo_strategy import RepoInfo
from ..load_configuration.conf_structures import ExtractInformation, TargetInformation

def repo_info_factory(target,info) -> str:

    repo = RepoInfo(
        repo_path=target.repo_path,
        branch=target.branch_name,
        start_date=target.start_date,
        end_date=target.end_date,
        output_dir="repoinfo_outputs",
        dependency_file=target.dependency_file_path,
        prog_lang=target.programing_language
    )
    
    hashes = repo.getHashes()

    if info == "diff":
        return repo.getDiffs(hashes)
    elif info == "commit_description":
        return repo.getCommits(hashes)
    elif info == "readme":
        return repo.getReadMe()
    
    # adicionar o resto das funções depois de testado

def get_repoinfo_dictionary(target: TargetInformation, info: ExtractInformation) -> Dict[str, str]:
    repoinfo_dict = {}
    print(info.types)

    for info_type in info.types:
        repoinfo_dict[info_type] = repo_info_factory(target,info_type)
    return repoinfo_dict