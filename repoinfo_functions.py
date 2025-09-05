from git import Repo
from datetime import datetime
import os
from collections import Counter

# Variáveis que virão do .config
repo_path = r"C:\Users\guicu\OneDrive\Documentos\prog\aise\GithubDocs" # caminho do repositório *OBRIGATÓRIO
branch = "main" # nome da branch      
start_date = "" # "YYYY-MM-DD"
end_date = "" # "YYYY-MM-DD"  
dependency_file = "requirements.txt" # nome do arquivo de dependências
repo_description = "Meu projeto de exemplo" # descrição/contexto do repositório
framework = "Django" # framework usado no projeto *OBRIGATÓRIO (pode ser "Nenhum")
prog_lang = "Python" # linguagem de programação principal *OBRIGATÓRIO (pode ser "Autodetect")

start_date = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
end_date = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None
### -----------------------------------------------------------------------------

repo = Repo(repo_path)
output_dir = "repoinfo_outputs"

print(f"Repositório: {repo_path}")
print(f"Branch: {branch}")
print(f"Descrição: {repo_description}")
print(f"Linguagem: {prog_lang}, Framework: {framework}")
print(f"Dependências: {dependency_file}\n")

def getCommits(branch="main", start_date=start_date, end_date=end_date, output_filename="commits.txt"):
    output_file = os.path.join(output_dir, output_filename)

    with open(output_file, "w", encoding="utf-8") as f:
        for commit in repo.iter_commits(branch):
            commit_date = commit.committed_datetime
            if start_date and commit_date < start_date:
                continue
            if end_date and commit_date > end_date:
                continue

            f.write(f"{commit.message.strip()}\n")
    print(f"Commits salvos em {output_file}")
    return output_file

def getCommitDiffs(branch="main", start_date=start_date, end_date=end_date, output_filename="diffs.txt"):
    output_file = os.path.join(output_dir, output_filename)

    with open(output_file, "w", encoding="utf-8") as f:
        commits = list(repo.iter_commits(branch))
        for i in range(len(commits)-1):
            commit = commits[i]
            parent = commits[i+1]  # commit anterior

            commit_date = commit.committed_datetime
            if start_date and commit_date < start_date:
                continue
            if end_date and commit_date > end_date:
                continue

            diffs = commit.diff(parent, create_patch=True)
            for diff in diffs:
                f.write(diff.diff.decode('utf-8', errors='ignore') + "\n")

    print(f"Diferenças salvas em {output_file}")
    return output_file

def getDependencies(dependency_file=dependency_file):
    return os.path.join(repo_path, dependency_file)

getDependencies()
getCommitDiffs()
getCommits()