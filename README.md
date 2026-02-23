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

#### GITHUB_TOKEN (Optional)
Optional token for **GitHub Issues integration**. The framework can work without it, but with reduced API rate limits (60 requests/hour vs 5000 with authentication).

**How to obtain a GitHub Personal Access Token:**
1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Select scopes: `repo` (for private repos) or `public_repo` (for public repos only)
4. Copy the generated token

**How to configure:**

Create a `.env` file in the project root:
```bash
GITHUB_TOKEN=your_token_here
```

Or set it directly in your environment:
```bash
# Linux/macOS
export GITHUB_TOKEN=your_token_here

# Windows PowerShell
$env:GITHUB_TOKEN="your_token_here"
```

**Note:** Without a token, GitHub Issues integration will still work but with GitHub's unauthenticated API rate limit (60 requests/hour instead of 5000/hour).

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

#### github_repo_name
Optional parameter to enable **GitHub Issues integration**. Specify the repository in the format `"owner/repo"`.

When configured, the framework will:
- Automatically detect issue references in commit messages (patterns like `#123`, `fix #456`, `closes #789`)
- Fetch detailed information about referenced issues via GitHub API
- Make issue data available to LLM agents through specialized tools
- Include issue context in documentation generation

**Requirements:**
- A GitHub Personal Access Token in the `GITHUB_TOKEN` environment variable is **recommended** for higher API rate limits
- Without a token, the GitHub API has a rate limit of 60 requests/hour
- The repository must be publicly accessible (or accessible with the provided token if private)

##### Example
```Python
github_repo_name = "stone-payments/pos-mamba-sdk"
```

**Note:** The framework works without a token but with reduced rate limits (60 requests/hour). For better performance, especially with repositories that have many issues, it's recommended to configure a token.

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

#### tools
Optional list of tool names that the LLM agent can use during execution. Tools extend the agent's capabilities beyond text generation.

**Available tool categories:**
- **GitHub Issues Tools** (automatically enabled when `github_repo_name` is configured):
  - `search_github_issues_in_commits`: Searches for issues mentioned in commit messages
  - `get_github_issue_details`: Retrieves detailed information about a specific issue
  - `extract_issue_numbers_from_text`: Extracts issue numbers from any text

When GitHub tools are enabled, the LLM agent can autonomously search for and retrieve issue information during documentation generation, providing richer context about bug fixes, feature implementations, and project evolution.

##### Example
```Python
tools = []  # No special tools (default)
# Tools are automatically available when github_repo_name is set
```

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
  * **`--issuelog`**: Prints **GitHub issues analysis** directly to the terminal instead of including it in the generated documentation. Useful for reviewing issue information without adding it to the output file. Automatically enabled when using `--debug`.

### Example with Flags

```bash
python main.py conf/config.toml --mock --debug
python main.py conf/config_mamba_test.toml --issuelog
```
---

# Templates

At the root of the project there is a **`prompt/`** folder, responsible for centralizing all prompts templates used by the LLMs (Gemini, ChatGPT, and local models).  
Each prompt is written in **Jinja**, allowing dynamic context injection (commits, diffs, files, outputs from previous steps, etc.).


## Baseline Prompts

The framework provides **three main baseline prompts** that cover the core documentation generation tasks:

### **1. changelog.jinja**  
Generates **changelogs** from commit history, diffs, and repository context.
- **Use case:** Automated release notes, version history documentation
- **Execution:** Single-step
- **Input:** Commit list, diffs, repository information

### **2. readme.jinja**  
Creates a **README from scratch** based on the project context.
- **Use case:** Initial documentation for new projects or complete rewrites
- **Execution:** Single-step
- **Input:** Repository structure, file tree, commits, license

### **3. readme_update.jinja**  
Updates an **existing README** intelligently, preserving structure and style.
- **Use case:** Keeping documentation up-to-date with code changes
- **Execution:** Single-step (default) or multi-step (see below)
- **Input:** Current README, recent commits, diffs, additional context


## Alternative Execution Flows

### Two-Step README Update

For scenarios requiring **greater control and safety** over automated changes, the framework supports a **two-step execution flow** for README updates.

This approach is available in `prompt/other-examples/two-step-flow/`:

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
template_path = "prompt/other-examples/two-step-flow/"
prompt_file = "verify_changes.jinja"
prompt_variables = {}
tools = []

[[agents.orchestration]]
step = 2
model_name = "gemini-2.5-flash"
temperature = 0.2
template_path = "prompt/other-examples/two-step-flow/"
prompt_file = "apply_changes.jinja"
prompt_variables = {}
tools = []
```

### Step-to-Step Communication

To enable chained multi-step execution, the framework uses the special variable:

```jinja
{{ last_step_output }}
```

This variable automatically injects into the current prompt the output generated by the previous step, allowing the LLM to:
- Analyze the previous result
- Refine the output
- Apply changes based on prior context


## Other Examples and Deprecated Files

The `prompt/other-examples/deprecated/` folder contains older experimental prompts that are **no longer actively used** but are kept for historical reference and potential future experimentation:

- **orchestration.jinja** - Generic repository analysis template

These files are not part of the main workflow but remain available for reference or testing alternative approaches

---

# GitHub Issues Integration

The framework includes powerful GitHub Issues integration, allowing LLM agents to automatically discover and analyze issues referenced in commits.

## Features

### Automatic Issue Detection
The framework automatically scans commit messages for issue references using various patterns:
- `#123` - Direct issue reference
- `fix #456`, `fixes #456`, `fixed #456` - Fix patterns
- `close #789`, `closes #789`, `closed #789` - Close patterns  
- `resolve #101`, `resolves #101`, `resolved #101` - Resolve patterns
- `issue-123`, `gh-123` - Alternative formats

### Issue Data Extraction
For each detected issue, the framework fetches:
- Title and description
- Current state (open/closed)
- Author information
- Labels and milestone
- Related pull requests
- Closing commit (if applicable)
- Creation and close timestamps

### LLM Agent Tools
When GitHub integration is enabled, LLM agents gain access to specialized tools:

**`search_github_issues_in_commits()`**  
Searches all commit messages for issue references and returns a summary of found issues with their details.

**`get_github_issue_details(issue_number: int)`**  
Retrieves comprehensive information about a specific issue, including description, timeline, and resolution context.

**`extract_issue_numbers_from_text(text: str)`**  
Extracts issue numbers from any given text using pattern matching.

These tools allow the LLM to autonomously gather issue context during documentation generation, producing more accurate and contextual documentation.

## Configuration Example

```toml
[target_information]
repo_path = "external_repos/pos-mamba-sdk"
branch_name = "master"
commit_list = ["abc123..def456"]
github_repo_name = "stone-payments/pos-mamba-sdk"  # Enable GitHub integration

[[agents.orchestration]]
step = 1
model_name = "gemini-2.5-flash"
template_path = "prompt/"
prompt_file = "changelog.jinja"
tools = []  # GitHub tools are automatically available
```

## Usage in Prompts

Issue data is automatically available in your Jinja templates when not using `--issuelog`:

```jinja
{% if issues_analysis %}
## Related Issues

This release addresses {{ issues_analysis.total_issues_referenced }} issue(s):

{% for issue_num, issue in issues_analysis.issues.items() %}
- **#{{ issue_num }}**: {{ issue.title }} ({{ issue.state }})
  - Author: {{ issue.author }}
  {% if issue.labels %}
  - Labels: {{ issue.labels | join(', ') }}
  {% endif %}
{% endfor %}
{% endif %}
```

## Terminal Output Mode

Use the `--issuelog` flag to print issue analysis to the terminal instead of including it in documentation:

```bash
python main.py conf/config.toml --issuelog
```

This displays a formatted report of all detected issues without adding them to the generated output file.