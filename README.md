# GithubDocs

Este projeto utiliza o [uv](https://github.com/astral-sh/uv), um instalador e gerenciador de pacotes Python ultra rápido que também inclui o linter/formatter Ruff.

Além disso, o projeto gerencia dependências de repositórios externos para a geração de documentação através de Git submodules.

## Instalação e Configuração

### 1. Pré-requisitos

Instale o `uv` em seu sistema:

  
#### Via curl (Linux/macOS)
``` bash
curl -Ls [https://astral.sh/uv/install.sh](https://astral.sh/uv/install.sh) | sh
```

#### Via pip
```bash
pip install uv
```

### 2\. Clonando o Repositório

Para clonar este repositório pela primeira vez, incluindo os submodules, use o comando:

```bash
git clone --recursive <this-repo-url>
```

Se você já clonou o repositório sem os submodules, inicialize-os com:

```bash
git submodule init
git submodule update
```

### 3\. Instalando Dependências Python

Com o repositório clonado, crie um ambiente virtual e instale as dependências:

```bash
# Instale as dependências do projeto
uv sync
```

## Uso

## Gerenciamento de Submodules

Este projeto usa Git submodules para gerenciar dependências de repositórios externos. Eles estão localizados no diretório `external_repos/`.

### Adicionando um Novo Submodule

Para adicionar um novo repositório como um submodule:

```bash
git submodule add <repository-url> external_repos/<repo-name>
```

### Atualizando Submodules

Para atualizar todos os submodules para seus commits mais recentes na branch padrão:

```bash
git submodule update --remote
```

Para atualizar um submodule específico:

```bash
git submodule update --remote external_repos/<repo-name>
```

### Folder creation

To run the application, you going to need to create other two folders in the repository, the outputs and the logs folder

you could do that running
```
mkdir output logs
```

# Configuration Documentation

## Config File

The config file needs to be referenced when running the application by passing it via arguments. In the `conf/` directory, there is a simple example that configures the framework to run on the EventFlow repository. Note that this example is not suitable for real test scenarios.

## Config File Structure

### [target_information]

This section provides information about the repository that will be used as the test subject.

#### repo_path
The git repository path. This can be either a full path to a location on your PC or a relative location within this repository. This variable does not have a default value.

Two verifications are performed with this information:
1. Check if the path actually exists
2. Verify if it is a valid git repository

#### branch_name
The specific branch you want to test. This variable does not have a default value.

#### start & end commit
These two variables represent the range between two commits that you want to explore.

**Caution:** When dealing with these values, note that the end commit is the most recent commit, and the start commit is the older one.

### [[agents.output]]

#### result & log paths
These are the paths the framework will use to write the expected results. It's important to note that the folders need to exist beforehand. If you do not create them, a "KeyError: Path does not exist" message will appear.

#### result_file_name
The file name you want to use for output. It's important to ensure this follows the pattern you specified in the prompt. There is no validation between the file extension and the output format.

### [[agents.orchestration]]

#### step
A simple number to define the execution order.

#### model_name
The actual name of the model from the LLM family (e.g., `gemini-2.5-flash`). Using just "gemini" will cause an error.

#### temperature
This represents the model temperature, a standard LLM parameter.

#### template_path
The path to the folder where the Jinja templates are located.

#### prompt_file
The actual prompt file created using Jinja templates.

#### prompt_variables
A simple dictionary of variables that can be used in the prompt.

**Example:**

```toml
# config.toml
{ repo = "EventFlow" }
```

```jinja
# prompt.jinja
What do you know about this GitHub repository {{repo}}?
```

## Prompt Creation

The prompt files are based on Jinja templates. Below is a basic usage example. For further information on Jinja templating functionalities, you can check this link: https://jinja.palletsprojects.com/en/stable/

**Example:**

```jinja
{% for commit in repo_info %}
Commit: {{ commit.hash }}
Author Date: {{ commit.date }}
Message: {{ commit.message }}
Modifications:
{% for file_path, modification in commit.modifications.items() %}
  File: {{ file_path }}
  Change Type: {{ modification.change_type }}
  Added Lines: {{ modification.added_lines }}
  Source code before: {{modification.source_code_before}}
  Diff:
  {{ modification.diff }}
{% endfor %}
{% endfor %}
```

This example is in the prompt folder with the name `orchestration.jinja`.

This prompt is rendered by a function that receives a dictionary. The dictionary we use internally has the following structure:

```python
commit_info = {
    "hash": "",
    "date": "",
    "message": "",
    "modifications": {
        "file_name_id": {
            "change_type": "",
            "added_lines": "",
            "diff": "",
            "source_code_before": ""
        }
    }
}
```

**Note:** `file_name_id` represents each changed file. The ID exists to separate possible different alterations when there are two separate additions to a file.
