import git
from datetime import datetime
from typing import List

class GitManager:
    def get_hashes(self, repo_path: str, branch: str, start_date: str = None, end_date: str = None) -> List[str]:
        repo = git.Repo(repo_path)
        
        since = None
        until = None
        
        if start_date:
            try:
                since = datetime.fromisoformat(start_date)
            except ValueError:
                since = datetime.strptime(start_date, '%Y-%m-%d')
                
        if end_date:
            try:
                until = datetime.fromisoformat(end_date)
            except ValueError:
                until = datetime.strptime(end_date, '%Y-%m-%d')
        
            commits = list(repo.iter_commits(
            rev=branch,
            since=since,
            until=until
        ))
        
        return [commit.hexsha for commit in commits]
    
    def get_commits(self, repo_path: str, hashes: List[str]) -> List[str]:
        repo = git.Repo(repo_path)
        messages = []
        
        for hash_commit in hashes:
            try:
                commit = repo.commit(hash_commit)
                messages.append(commit.message)
            except git.BadName:
                messages.append("")
                
        return messages
    
    def get_diffs(self, repo_path: str, hashes: List[str]) -> str:
        if len(hashes) < 2:
            return ""
            
        repo = git.Repo(repo_path)
        
        try:
            start_commit = repo.commit(hashes[-1])
            end_commit = repo.commit(hashes[0])
            
            diff = repo.git.diff(start_commit.hexsha, end_commit.hexsha)
            return diff
            
        except git.BadName:
            return ""
    
    def get_commit_info(self, repo_path: str, hash_commit: str) -> dict:
        repo = git.Repo(repo_path)
        try:
            commit = repo.commit(hash_commit)
            return {
                'hash': commit.hexsha,
                'short_hash': commit.hexsha[:7],
                'message': commit.message.strip(),
                'author': str(commit.author),
                'author_email': commit.author.email,
                'date': commit.committed_datetime,
                'files_changed': [item.a_path for item in commit.stats.files.keys()]
            }
        except git.BadName:
            return {}
    
    def get_branches(self, repo_path: str) -> List[str]:
        repo = git.Repo(repo_path)
        return [str(branch) for branch in repo.branches]
    
    def get_current_branch(self, repo_path: str) -> str:
        repo = git.Repo(repo_path)
        return str(repo.active_branch)
    
    def get_repo_tree(self, repo_path: str, hash_commit: str = 'HEAD') -> List[str]:
        repo = git.Repo(repo_path)
        try:
            commit = repo.commit(hash_commit)
            return [item.path for item in commit.tree.traverse()]
        except git.BadName:
            return []
    
    def get_repo_name(self, repo_path: str) -> str:
        repo = git.Repo(repo_path)
        return repo.working_tree_dir.split('/')[-1]
        
    def get_tags(self, repo_path: str) -> List[str]:
        repo = git.Repo(repo_path)
        return [str(tag) for tag in repo.tags]
    
    def get_readme_content(self, repo_path: str) -> str:
        import os
        
        readme_files = ['README.md', 'README.txt', 'README']
        for readme in readme_files:
            readme_path = os.path.join(repo_path, readme)
            if os.path.isfile(readme_path):
                with open(readme_path, 'r', encoding='utf-8') as f:
                    return f.read()
        return ""
    
    def get_dict_of_repo_info(self, repo_path: str, branch: str, start_date: str = None, end_date: str = None) -> dict:
        hashes = self.get_hashes(repo_path, branch, start_date, end_date)
        commits = self.get_commits(repo_path, hashes)
        diffs = self.get_diffs(repo_path, hashes)
        branches = self.get_branches(repo_path)
        repo_tree = self.get_repo_tree(repo_path)
        tags = self.get_tags(repo_path)
        readme_content = self.get_readme_content(repo_path)
        repo_name = self.get_repo_name(repo_path)

        return {
            'hashes': hashes,
            'commit': commits,
            'diff': diffs,
            'branches': branches,
            'repo_tree': repo_tree,
            'tags': tags,
            'readme': readme_content,
            'repo_name': repo_name
        }
    
    def git_pull(self, repo_path: str, branch: str = 'main') -> None:
        repo = git.Repo(repo_path)
        origin = repo.remotes.origin
        origin.pull(branch)

    def checkout_branch(self, repo_path: str, branch: str) -> None:
        repo = git.Repo(repo_path)
        repo.git.checkout(branch)
    
