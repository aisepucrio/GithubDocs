from langchain.tools import tool
from git import Repo
'''
@tool("git_file_tree_at_commit",description="Get the file tree of the repository at a specific commit hash. Input is a commit hash string, output is a newline-separated list of file paths.")
def get_file_tree_at_commit(self, commit_hash: str) -> str:                                                                                                                  
      """Returns the file tree at a specific commit."""                                                                                                                        
      repo = Repo(self.repository_path)                                                                                                                                        
      commit = repo.commit(commit_hash)                                                                                                                                        
                                                                                                                                                              
      file_tree = []                                                                                                                                                           
      excluded = {'.git', '__pycache__', 'node_modules', '.venv', 'venv'}                                                                                                      
      excluded.update(self.ignored_files)                                                                                                                                      
                                                                                                                                                                               
      for item in commit.tree.traverse():                                                                                                                                      
          if any(part in excluded for part in item.path.split('/')):                                                                                                           
              continue                                                                                                                                                         
          file_tree.append(item.path)                                                                                                                                          
                                                                                                                                                                               
      return "\n".join(sorted(file_tree))                                                                                                                                      
                                                                                                                                                                               
                                                                                                                                                                               
def get_file_at_commit(self, commit_hash: str, file_path: str) -> str:                                                                                                       
      """Returns the content of a specific file at a specific commit."""                                                                                                       
      repo = Repo(self.repository_path)                                                                                                                                        
      commit = repo.commit(commit_hash)                                                                                                                                        
                                                                                                                                                                               
      try:                                                                                                                                                                     
          blob = commit.tree / file_path                                                                                                                                       
          return blob.data_stream.read().decode("utf-8", errors="replace")                                                                                                     
      except KeyError:                                                                                                                                                         
          raise FileNotFoundError(f"{file_path} not found at {commit_hash}")                                                                                                   

@tool                                                                                                                                                                                                                                                                         
def search_in_repo_at_commit(self, commit_hash: str, search_term: str, case_sensitive: bool = False) -> str:                                                                       
      """Searches for a term across all files in the repo at a specific commit.                                                                                                
      Returns matching files with line numbers and content."""                                                                                                                 
      repo = Repo(self.repository_path)                                                                                                                                             
      commit = repo.commit(commit_hash)                                                                                                                                        
                                                                                                                                                                               
      excluded = {'.git', '__pycache__', 'node_modules', '.venv', 'venv'}                                                                                                      
      results = []                                                                                                                                                             
                                                                                                                                                                               
      for item in commit.tree.traverse():                                                                                                                                      
          if item.type != 'blob':                                                                                                                                              
              continue                                                                                                                                                         
          if any(part in excluded for part in item.path.split('/')):                                                                                                           
              continue                                                                                                                                                         
                                                                                                                                                                               
          try:                                                                                                                                                                 
              content = item.data_stream.read().decode("utf-8", errors="replace")                                                                                              
              lines = content.splitlines()                                                                                                                                     
                                                                                                                                                                               
              for line_num, line in enumerate(lines, 1):                                                                                                                       
                  compare_line = line if case_sensitive else line.lower()                                                                                                      
                  compare_term = search_term if case_sensitive else search_term.lower()                                                                                        
                                                                                                                                                                               
                  if compare_term in compare_line:                                                                                                                             
                      results.append(f"{item.path}:{line_num}: {line.strip()}")                                                                                                
          except Exception:                                                                                                                                                    
              continue  # Skip binary files                                                                                                                                    
                                                                                                                                                                               
      if not results:                                                                                                                                                          
          return f"No matches found for '{search_term}'"                                                                                                                       
                                                                                                                                                                               
      return "\n".join(results)           
'''