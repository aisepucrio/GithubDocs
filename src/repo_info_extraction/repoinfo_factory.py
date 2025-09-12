from typing import Dict, Any, List
from .repoinfo_strategy import RepoInfo
from src.load_configuration.conf_structures import ExtractInformation  

def repo_info_factory(repo_path: str, extract_config: ExtractInformation) -> Dict[str, Any]:
    repo = RepoInfo()
    if info == "diff":
        return 

class RepoInfoFactory:
    def __init__(self, repo_path: str, extract_config: ExtractInformation):
        self.repo_path = repo_path
        self.extract_config = extract_config

    def create(self) -> Dict[str, Any]:
        """
        Cria uma instância de RepoInfo e retorna apenas as partes solicitadas em extract_config.types
        """
        repo = RepoInfo(repo_path=self.repo_path)

        result: Dict[str, Any] = {}
        for info_type in self.extract_config.types:
            if info_type == "hashes":
                result["hashes"] = repo.getHashes()
            elif info_type == "commits":
                hashes = repo.getHashes()
                result["commits"] = repo.getCommits(hashes, "commits.txt")
            elif info_type == "diffs":
                hashes = repo.getHashes()
                result["diffs"] = repo.getDiffs(hashes, "diffs.txt")
            elif info_type == "tree":
                result["tree"] = repo.getTree()
            elif info_type == "dependencies":
                result["dependencies"] = repo.getDependencies()
            elif info_type == "languages":
                result["languages"] = repo.getProgrammingLanguages()
            else:
                raise ValueError(f"Tipo de extração não suportado: {info_type}")

        return result
