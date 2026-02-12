from langchain.tools import tool
from git import Repo
import os
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

from langchain.tools import tool

@tool
def soma(a: float, b: float) -> float:
    """Soma dois números."""
    print("a + b = ", a + b)
    return a + b


@tool
def subtrai(a: float, b: float) -> float:
    """Subtrai b de a."""
    print("a - b = ", a-b)
    return a - b


@tool
def multiplica(a: float, b: float) -> float:
    """Multiplica dois números."""
    print("a * b = ",a * b)
    return a * b


@tool
def divide(a: float, b: float) -> float:
    """Divide a por b. Lança erro se b for zero."""
    if b == 0:
        raise ValueError("Divisão por zero não é permitida.")
    print("a / b = ",a / b)
    return a / b

@tool
def read_file(file_path: str) -> str:
    """Opens a file by its path and returns its content as text."""
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File '{file_path}' not found.")
    
    if not os.path.isfile(file_path):
        raise ValueError(f"'{file_path}' is not a valid file.")
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        raise RuntimeError(f"Error reading file: {str(e)}")

@tool
def save_readme(content: str) -> str:
    """
    Saves the provided content as README.md inside the 'output' folder.
    """

    try:
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)

        file_path = os.path.join(output_dir, "README.md")

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return f"README saved successfully at: {file_path}"

    except Exception as e:
        return f"Error saving README: {str(e)}"

ALL_TOOLS = {
    "soma": soma,
    "subtrai": subtrai,
    "multiplica": multiplica,
    "divide": divide,
}