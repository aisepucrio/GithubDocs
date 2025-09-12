import os
import subprocess

class RepoInfo:
    def __init__(self, repo_path, branch="main",
                 start_date=None, end_date=None,
                 output_dir="repoinfo_outputs",
                 dependency_file="requirements.txt",
                 prog_lang="Autodetect"):
        self.repo_path = repo_path
        self.output_dir = output_dir
        self.dependency_file = dependency_file
        self.prog_lang = prog_lang
        self.branch = branch
        self.start_date = start_date
        self.end_date = end_date

        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def getHashes(self):
        cmd = ["git", "log", self.branch, "--pretty=format:%H"]
        if self.start_date:
            cmd += [f"--since={self.start_date}"]
        if self.end_date:
            cmd += [f"--until={self.end_date}"]

        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", cwd=self.repo_path)
        return result.stdout.splitlines()


    def getCommits(self, hashes, output_filename="commits.txt"):
        output_file = os.path.join(self.output_dir, output_filename)

        messages = []
        for h in hashes:
            cmd = ["git", "log", "-1", "--pretty=format:%B", h]
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.repo_path, encoding="utf-8")
            messages.append(result.stdout)

        with open(output_file, "w", encoding="utf-8") as f:
            for line in messages:
                f.write(line + "\n")

        print(f"{len(messages)} mensagens de commit salvas em {output_file}")
        return messages

    def getDiffs(self, hashes, output_filename="diffs.txt"):
        output_file = os.path.join(self.output_dir, output_filename)

        start_hash = hashes[-1]
        end_hash = hashes[0]

        cmd = ["git", "diff", start_hash, end_hash]

        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", cwd=self.repo_path)
        diff_text = result.stdout if result.stdout else ""

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(diff_text)

        print(f"Diffs salvos em {output_file}")
        return diff_text

    def getCodeRelatedToDiffs(self, hashes, output_filename="code_related_to_diffs.txt"):
        output_file = os.path.join(self.output_dir, output_filename)

        start_hash = hashes[-1]
        end_hash = hashes[0]

        cmd = ["git", "diff", start_hash, end_hash, "--unified=0"]

        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", cwd=self.repo_path)
        diff_text = result.stdout if result.stdout else ""

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(diff_text)

        print(f"Diffs salvos em {output_file}")
        return diff_text

    def getDependencies(self):
        return os.path.join(self.repo_path, self.dependency_file)

    def getProgrammingLanguages(self):
        prog_exts = {
            ".py", ".js", ".ts", ".java", ".c", ".cpp", ".cs", ".rb", ".go",
            ".php", ".rs", ".swift", ".kt", ".m", ".scala", ".sh", ".r",
            ".jl", ".dart", ".hs", ".lua", ".pl", ".sql", ".ipynb", ".fs",
            ".ex", ".exs", ".v", ".vhd", ".vhdl", ".groovy", ".clj", ".cljs",
            ".elm", ".erl", ".nim", ".cr", ".coffee", ".tsx", ".jsx"
        }

        if self.prog_lang != "Autodetect":
            return self.prog_lang

        langs_found = set()
        for root, dirs, files in os.walk(self.repo_path):
            if ".git" in dirs:
                dirs.remove(".git")

            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in prog_exts:
                    langs_found.add(ext)

        return ", ".join(sorted(langs_found)) if langs_found else None

    def getTree(self, path=None, include_venv_files=False, _prefix=''):
        if path is None:
            path = self.repo_path

        entries = sorted(os.listdir(path))
        entries = [e for e in entries if e != '.git' and (include_venv_files or e != 'venv')]
        entries_count = len(entries)

        lines = []
        for idx, entry in enumerate(entries):
            full_path = os.path.join(path, entry)
            is_last = idx == entries_count - 1
            connector = '└── ' if is_last else '├── '
            lines.append(f"{_prefix}{connector}{entry}")

            if os.path.isdir(full_path):
                new_prefix = _prefix + ('    ' if is_last else '│   ')
                lines.append(self.getTree(full_path, include_venv_files, _prefix=new_prefix))

        tree = '\n'.join(lines)

        return tree
    
<<<<<<< HEAD
    return hashes

def getCommits(hashes, output_filename):
    output_file = os.path.join(output_dir, output_filename)

    messages = []
    for h in hashes:
        cmd = ["git", "log", "-1", "--pretty=format:%B", h]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=repo_path, encoding="utf-8")
        messages.append(result.stdout)

    with open(output_file, "w", encoding="utf-8") as f:
        for line in messages:
            f.write(line + "\n")

    print(f"{len(messages)} mensagens de commit salvas em {output_file}")

    return messages
    
def getDiffs(hashes,output_filename):
    output_file = os.path.join(output_dir, output_filename) 

    start_hash = hashes[-1]
    end_hash = hashes[0]

    cmd = ["git", "diff", start_hash, end_hash]

    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", cwd=repo_path)

    diff_text = result.stdout if result.stdout else ""

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(diff_text)

    print(f"Diffs salvos em {output_file}")

    return diff_text

def getCodeReletadToDiffs(hashes,output_filename):
    output_file = os.path.join(output_dir, output_filename) 

    start_hash = hashes[-1]
    end_hash = hashes[0]

    cmd = ["git", "diff", start_hash, end_hash, "--unified=0"]

    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", cwd=repo_path)

    diff_text = result.stdout if result.stdout else ""

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(diff_text)

    print(f"Diffs salvos em {output_file}")

    return diff_text

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

def getTree(path='.', include_venv_files=False, _prefix=''):
    entries = sorted(os.listdir(path))
    # ignora .git e .venv (se include_venv_files=False)
    entries = [e for e in entries if e != '.git' and (include_venv_files or e != 'venv')]
    entries_count = len(entries)
    
    lines = []
    
    for idx, entry in enumerate(entries):
        full_path = os.path.join(path, entry)
        is_last = idx == entries_count - 1
        connector = '└── ' if is_last else '├── '
        lines.append(f"{_prefix}{connector}{entry}")
        
        if os.path.isdir(full_path):
            new_prefix = _prefix + ('    ' if is_last else '│   ')
            lines.append(getTree(full_path, include_venv_files, _prefix=new_prefix))
    
    tree = '\n'.join(lines)
    print(tree)
    return tree

# ------------------- Execução -------------------
if __name__ == "__main__":
    print(f"Linguagens detectadas: {getProgrammingLanguages()}")
    print(f"Dependências: {getDependencies()}")

    hashes = getHashes(branch=branch, start_date=start_date, end_date=end_date)
    getCommits(hashes,output_filename="commits.txt")
    getDiffs(hashes,"diffs.txt")
    getCodeReletadToDiffs(hashes,"diffs_related_code.txt")
    getTree()


=======
    def getReadMe(self):
        root_dir = os.getcwd()
        readme_path = os.path.join(root_dir, "README.md")
        if not os.path.isfile(readme_path):
            raise FileNotFoundError(f"README.md não existe em {root_dir}")
        with open(readme_path, "r", encoding="utf-8") as f:
            readme = f.read()
        return readme
>>>>>>> refs/remotes/origin/main
