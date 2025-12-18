# GithubDocs

This project utilizes [uv](https://github.com/astral-sh/uv), an ultra-fast Python package installer and manager that also includes the Ruff linter/formatter.

Additionally, the project manages dependencies from external repositories for documentation generation via Git submodules.

## Installation and Setup

### 1. Prerequisites

Install `uv` on your system:

  
#### Via curl (Linux/macOS)
``` bash
# for Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# for Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

#### Via pip
```bash
pip install uv
```

### 2\. Cloning the Repository

To clone this repository for the first time, including submodules, use the command:

```bash
git clone --recursive <this-repo-url>
```

If you have already cloned the repository without submodules, initialize them with:

```bash
git submodule init
git submodule update
```

### 3\. Installing Python Dependencies

With the repository cloned, create a virtual environment and install the dependencies:

```bash
# Install project dependencies
uv sync
```

## Usage

## Submodule Management

This project uses Git submodules to manage dependencies from external repositories. They are located in the `external_repos/` directory.

### Adding a New Submodule

To add a new repository as a submodule:

```bash
git submodule add <repository-url> external_repos/<repo-name>
```

### Updating Submodules

To update all submodules to their latest commits on the default branch:

```bash
git submodule update --remote
```

To update a specific submodule:

```bash
git submodule update --remote external_repos/<repo-name>
```

### Folder Creation

To run the application, you will need to create two folders in the repository: `output` and `logs`.

You can create these folders by running the following command:
```bash
mkdir output logs
```

# Configuration Documentation

## Config File

The configuration file must be passed as an argument when running the application. The `conf/` directory contains a simple example that sets up the framework to analyze the EventFlow repository. Please note that this example is intended for demonstration purposes only and is not suitable for real test scenarios.

## Config File Structure

### [target_information]

This section specifies the target repository that will be analyzed.

#### repo_path
The path to the Git repository. This can be an absolute path on your file system or a relative path within this project. This variable is mandatory and does not have a default value.

Two validations are performed on this path:
1.  Checks if the specified path exists.
2.  Verifies if it is a valid Git repository.

#### branch_name
The specific branch of the repository you wish to analyze. This variable is mandatory and does not have a default value.

#### start & end commit
These two variables define the range of commits you want to explore. The framework will analyze all commits from `start_commit` up to and including `end_commit`.

**Caution:** The `end_commit` should be a more recent commit than the `start_commit`. If `start_commit` is more recent than `end_commit`, the range will be empty.

### [[agents.output]]

#### result & log paths
These paths specify where the framework will write the generated results and logs. It is crucial that these directories exist before running the application. If they do not exist, a `KeyError: Path does not exist` will occur.

#### result_file_name
The desired file name for the output. Ensure this adheres to any naming conventions specified in your prompt. There is no automatic validation between the file extension and the actual output format.

### [[agents.orchestration]]

This section configures the orchestration of agents, defining their execution order and model parameters.

#### step
A numerical value defining the execution order of this agent within the orchestration sequence. Lower numbers execute first.

#### model_name
The specific name of the Large Language Model (LLM) to use (e.g., `gemini-2.5-flash`). Using a generic name like `gemini` will result in an error.

#### temperature
This parameter controls the randomness of the model's output. It is a standard LLM parameter, typically a float between 0.0 and 1.0.

#### template_path
The absolute or relative path to the directory containing your Jinja prompt templates.

#### prompt_file
The name of the Jinja template file (e.g., `my_prompt.jinja`) that will be rendered to create the actual prompt sent to the LLM.

Jinja is a powerful templating tool that allows for dynamic prompt generation. It enables you to embed Python logic within your prompt files, making it possible to create highly flexible and robust prompts that can adapt to varying inputs and scenarios.

#### prompt_variables
These are simple key-value pairs that can be passed into your Jinja prompt templates. They are accessible within the template using the `{{ variable_name }}` syntax. The variables are defined as a dictionary.

Example of `prompt_variables` in the configuration:

```python
{repo_name = "EventFlow", repo_description= "EventFlow is a basic CQRS+ES framework designed to be easy to use."}

```
This variable could appear in the prompt where you mention it between curly braces. Example:
```jinja
Use the following repository data:
Repository Name: {{ repo_name }}
Repository Description: {{ repo_description }}
Repository Language: {{ repo_info.extensions }}
License: {{ repo_info.license }}
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

This example is in the `prompt` folder with the name `orchestration.jinja`.

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

**Note:** `file_name_id` acts as a unique identifier for each changed file within the `modifications` dictionary. All information automatically extracted from the repository will be placed into this structure.

# Running the Project

You must pass the path to a **configuration file** as an argument to `main.py`. Ensure that this configuration file follows the **TOML format**.

### Basic Execution

```bash
python main.py conf/config.toml
```
-----

### Optional Flags

The project supports two additional optional flags:

  * **`--debug`**: Enables **verbose logging** for enhanced troubleshooting.
  * **`--mock`**: Prints the **rendered AI prompt** (based on your configuration) directly to the terminal without sending it to the external AI service. This flag is **intended solely for testing and verification purposes**.

### Example with Flags

```bash
python main.py conf/config.toml --mock --debug
```