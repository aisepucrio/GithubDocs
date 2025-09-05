from git import Repo
from datetime import datetime
import os

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

getCommits()