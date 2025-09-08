from git import Repo
import os
import subprocess

# ------------------- Configurações -------------------
repo_path = r"C:\Users\guicu\OneDrive\Documentos\prog\aise\GithubDocs"  # caminho do repositório *OBRIGATÓRIO
branch = "Guilherme"  # nome da branch
start_date = "2025-09-01"  # "YYYY-MM-DD"
end_date = ""  # "YYYY-MM-DD"
dependency_file = "requirements.txt"  # nome do arquivo de dependências
repo_description = "Meu projeto de exemplo"  # descrição/contexto do repositório
framework = "Django"  # framework usado no projeto *OBRIGATÓRIO (pode ser "Nenhum")
prog_lang = "Autodetect"  # linguagem de programação principal *OBRIGATÓRIO (pode ser "Autodetect")
output_dir = os.path.join(repo_path, "repoinfo_outputs")

# ------------------- Repositório -------------------

output_dir = "repoinfo_outputs"
os.makedirs(output_dir, exist_ok=True)

print(f"Repositório: {repo_path}")
print(f"Branch: {branch}")
print(f"Descrição: {repo_description}")
print(f"Linguagem: {prog_lang}, Framework: {framework}")
print(f"Dependências: {dependency_file}\n")

# ------------------- Funções -------------------
def getCommits(branch="main", start_date=None, end_date=None, output_filename=None):
    output_file = os.path.join(output_dir, output_filename) if output_filename else None

    cmd = ["git", "log", branch]

    cmd += ["--pretty=format:%H %s"]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"Erro ao executar git log: {result.stderr}")

    commits = result.stdout.splitlines()

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            for c in commits:
                f.write(c + "\n")

    return commits



def getDependencies(dependency_file=dependency_file):
    return os.path.join(repo_path, dependency_file)


def getProgrammingLanguages(prog_lang=prog_lang, repo_path=repo_path):  # melhorar autodetect
    prog_exts = {
        ".py", ".js", ".ts", ".java", ".c", ".cpp", ".cs", ".rb", ".go",
        ".php", ".rs", ".swift", ".kt", ".m", ".scala", ".sh", ".r",
        ".jl", ".dart", ".hs", ".lua", ".pl", ".sql", ".ipynb", ".fs",
        ".ex", ".exs", ".v", ".vhd", ".vhdl", ".groovy", ".clj", ".cljs",
        ".elm", ".erl", ".nim", ".cr", ".coffee", ".tsx", ".jsx"
    }

    if prog_lang != "Autodetect":
        return prog_lang

    langs_found = set()
    for root, dirs, files in os.walk(repo_path):
        if ".git" in dirs:
            dirs.remove(".git")

        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in prog_exts:
                langs_found.add(ext)

    return ", ".join(sorted(langs_found)) if langs_found else None

# ------------------- Execução -------------------
print(f"Linguagens detectadas: {getProgrammingLanguages()}")
print(f"Dependências: {getDependencies()}")
getCommits(branch=branch, start_date=start_date, end_date=end_date,output_filename="commits.txt")

