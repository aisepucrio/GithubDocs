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

### Manual run

The old command still works:

```bash
python main.py conf/config.toml
```

You can also use the explicit subcommand:

```bash
python main.py run conf/config.toml
```

### Langfuse evaluation

The full evaluation workflow is now centralized in a single command:

```bash
python main.py eval /path/to/eval.csv
```

This single command handles:

- CSV -> Langfuse dataset
- experiment execution with the real GithubDocs pipeline
- waiting for evaluator scores
- exporting the final CSV

Example:

~~~bash
python main.py eval "/path/to/eval.csv"
~~~

## Submodule Management

This project uses Git submodules to manage external repositories used as test subjects. They are located in the `external_repos/` directory.
The GitModules is just used as Formality and Testability. You could find interest cases, about this git modules, to test in this google sheets: https://docs.google.com/spreadsheets/d/1tR-glo3Wky11PWpasvBAdzWIHSlkXx9W76VPLKVU_Vk/edit?gid=911701213#gid=911701213.

You also could specify repositories in your computer that are not in the git modules, see more about the variable **repo_path** in the "Config File Structure".

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

### Environment Variables

The framework uses environment variables for sensitive configuration:

#### LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY (Optional)
Optional keys to enable [Langfuse](https://langfuse.com/) tracing for the LLM calls. If these are set, the application will automatically send telemetry and traces of the agent executions (prompts sent, tokens consumed, etc.) to your Langfuse dashboard.

**How to configure:**

Create a `.env` file in the project root:
```bash
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_TRACING_ENVIRONMENT=development
# Optionally, if using a self-hosted instance:
LANGFUSE_HOST=http://localhost:3000
```

When enabled, GithubDocs creates a top-level `githubdocs-manual-run` trace for
each CLI run, nests LangChain model/tool observations under it, adds model and
repository metadata, and flushes pending events before the process exits.

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

#### commit_list
Commit list as the name suggests, is a list of commits separated by a comma. You can also simplify a range of commits by adding a colon or two dots between two commits. You could check the examples below.

##### Range example
```Python
commit_list = ["a962c3657a3c90f5132a479ab6aac4fbbade9996:bb820fef78d2b8476733d9b21fa7cce1421a7ba3"]
```

##### Distinct example
``` Python
commit_list = ["6bcade563d627ea3d2b35f59d4d5dee56d6ea6a","a962c3657a3c90f5132a479ab6aac4fbbade9996"]
```

#### ignore_files
Optional list of file paths or patterns to exclude from repository analysis. You can use glob patterns for flexible matching.

**`"IGNORED_PRESET"`** - Uses a pre-configured list of commonly ignored files and directories including:
- Lock files (package-lock.json, yarn.lock, etc.)
- Dependency directories (node_modules, vendor, etc.)
- Media files (images, videos, audio)
- Build outputs (dist, build, target, etc.)
- IDE configurations (.vscode, .idea, etc.)
- And more...

##### Examples
```Python
# Use preset only
ignore_files = ["IGNORED_PRESET"]

# Use preset + additional files
ignore_files = ["IGNORED_PRESET", "README.md", "docs/**"]

# Custom list
ignore_files = ["*.log", "temp/**", "config.json"]
```

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

> **Note on tools:** Orchestration steps do not accept a per-step `tools` setting. Tool calling is enabled globally via the `--tool-calling` CLI flag (see [Optional Flags](#optional-flags)). When active, the agent receives tools backed by the `RepoInfoExtractor` and fetches repository data on demand instead of having everything embedded in the prompt.

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

The project supports the following optional flags:

  * **`--debug`**: Enables **verbose logging** for enhanced troubleshooting.
  * **`--mock`**: Prints the **rendered AI prompt** (based on your configuration) directly to the terminal without sending it to the external AI service. This flag is **intended solely for testing and verification purposes**.
  * **`--tool-calling`**: Runs each step in **tool-calling mode**. Instead of embedding all repository data in the prompt, the agent is given tools backed by the `RepoInfoExtractor` (file tree, file contents and search at a given commit) and pulls data on demand. Uses the leaner templates under `prompt/tool-calling/`.

### Example with Flags

```bash
python main.py conf/config.toml --mock --debug
python main.py conf/config.toml --tool-calling
```
---

# Templates

At the root of the project there is a **`prompt/`** folder, responsible for centralizing all prompt templates used by the LLMs (Gemini, ChatGPT, and local models).  
Each prompt is written in **Jinja**, allowing dynamic context injection (commits, diffs, files, outputs from previous steps, etc.).

The templates are organized into **task-specific subfolders**:
- **`prompt/changelog/`** - Changelog generation templates
- **`prompt/readme/`** - README creation templates
- **`prompt/readme-update/`** - README update templates
- **`prompt/other-examples/`** - Experimental and deprecated templates


## Baseline Prompts

The framework provides **three main baseline prompts** that cover the core documentation generation tasks:

### **1. changelog.jinja**  
**Location:** `prompt/changelog/changelog.jinja`

Generates **changelogs** from commit history, diffs, and repository context.
- **Use case:** Automated release notes, version history documentation
- **Execution:** Single-step
- **Input:** Commit list, diffs, repository information

**Configuration example:**
```toml
[[agents.orchestration]]
step = 1
model_name = "gemini-2.5-flash"
temperature = 0.2
template_path = "prompt/changelog/"
prompt_file = "changelog.jinja"
```

### **2. readme.jinja**  
**Location:** `prompt/readme/readme.jinja`

Creates a **README from scratch** based on the project context.
- **Use case:** Initial documentation for new projects or complete rewrites
- **Execution:** Single-step
- **Input:** Repository structure, file tree, commits, license

**Configuration example:**
```toml
[[agents.orchestration]]
step = 1
model_name = "gemini-2.5-flash"
temperature = 0.2
template_path = "prompt/readme/"
prompt_file = "readme.jinja"
```

### **3. readme_update.jinja**  
**Location:** `prompt/readme-update/readme_update.jinja`

Updates an **existing README** intelligently, preserving structure and style.
- **Use case:** Keeping documentation up-to-date with code changes
- **Execution:** Single-step (default) or multi-step (see below)
- **Input:** Current README, recent commits, diffs, additional context

**Configuration example:**
```toml
[[agents.orchestration]]
step = 1
model_name = "gemini-2.5-flash"
temperature = 0.2
template_path = "prompt/readme-update/"
prompt_file = "readme_update.jinja"
```


## Alternative Execution Flows

### Two-Step README Update

For scenarios requiring **greater control and safety** over automated changes, the framework supports a **two-step execution flow** for README updates.

This approach is available in `prompt/readme-update/two-step-flow/`:

**Step 1: verify_changes.jinja**  
- Analyzes the repository context (commits, diffs, current README)
- Identifies **only the sections that need updates**
- Returns a structured list of proposed modifications
- **Does not apply changes directly**

**Step 2: apply_changes.jinja**  
- Receives the output from `verify_changes.jinja`
- Generates Git-style unified diffs for the proposed changes
- Preserves the README's structure, formatting, and tone
- Applies modifications in a controlled manner

#### How to Use Two-Step Flow

Configure your `config.toml` with two sequential orchestration steps:

```toml
[[agents.orchestration]]
step = 1
model_name = "gemini-2.5-flash"
temperature = 0.2
template_path = "prompt/readme-update/two-step-flow/"
prompt_file = "verify_changes.jinja"
prompt_variables = {}

[[agents.orchestration]]
step = 2
model_name = "gemini-2.5-flash"
temperature = 0.2
template_path = "prompt/readme-update/two-step-flow/"
prompt_file = "apply_changes.jinja"
prompt_variables = {}
```

## Other Examples and Deprecated Files

The `prompt/other-examples/deprecated/` folder contains older experimental prompts that are **no longer actively used** but are kept for historical reference and potential future experimentation:

- **orchestration.jinja** - Generic repository analysis template

These files are not part of the main workflow but remain available for reference or testing alternative approaches
