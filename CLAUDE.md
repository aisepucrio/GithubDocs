# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GithubDocs is an AI-powered documentation generation tool that analyzes Git commit history and generates/updates README files, changelogs, and other docs using LLMs (Gemini, OpenAI, Ollama).

## Commands

### Setup
```bash
uv sync                  # Install dependencies
mkdir -p output logs     # Required output directories
```

### Run
```bash
python main.py conf/config.toml            # Generate documentation
python main.py conf/config.toml --debug    # Verbose logging
python main.py conf/config.toml --mock     # Dry run (no API calls)
python main.py conf/config.toml --issuelog # Include GitHub Issues context
python main.py eval "/path/to/eval.csv"    # Langfuse evaluation pipeline
```

### Benchmark
```bash
python -m benchmark "1-20"           # Run rows 1-20 from Google Sheets config
python -m benchmark "1-5,10"         # Specific rows
python -m benchmark "all" --no-export
python -m benchmark "1" --local      # Use local test configs instead of Sheets
```

### Lint
```bash
ruff check .    # Lint
ruff format .   # Format (line length: 88)
```

## Architecture

### Execution Flow
```
main.py (CLI)
  → src/facade.py::start()             # Orchestration entry point
    → load_configuration/              # Parse TOML config into Pydantic models
    → repo_info_extraction/            # Extract commits/diffs via PyDriller
    → github_integration/              # Optional: fetch GitHub Issues context
    → llm_agent/                       # Render Jinja2 prompt → call LLM → return output
      → langfuse_integration.py        # Tracing callbacks (optional)
    → Write output file
```

### Key Modules
- **`src/facade.py`** — Main orchestrator. Runs agents sequentially, manages Jinja context, writes output.
- **`src/load_configuration/conf_structures.py`** — Pydantic models (`BaseAppConfig`, `OrchestrationStep`, `TargetInfo`). TOML config is validated here. Contains `IGNORE_FILES_PRESET` (200+ ignored file patterns).
- **`src/llm_agent/agent_interface.py`** — Abstract `AIAgent` base class. Concrete implementations in `agents_strategy.py` (Gemini, OpenAI, Ollama via LangChain).
- **`src/repo_info_extraction/repo_extractor.py`** — PyDriller wrapper. Extracts commits, diffs, file trees, README, license for a given branch/commit range.
- **`src/github_integration/issue_tracker.py`** — Detects issue references in commit messages (`#123`, `fix #456`) and fetches metadata from GitHub API.
- **`benchmark/`** — End-to-end test/eval pipeline. Loads configs from Google Sheets (or local fallback), runs the pipeline, exports results to Langfuse and Sheets.

### Configuration
Config files are TOML with three main sections:
- `[target_information]` — repo path, branch, commit range
- `[agents.output]` — output file path and naming
- `[[agents.orchestration]]` — one entry per LLM step: model, template path, temperature

Prompt templates use Jinja2 and live in `prompt/`. Template variables are populated from repository extraction results.

### Summarization Strategies
For large documents that exceed context windows, two strategies exist:
- **Refine** — iteratively refines a running summary chunk by chunk
- **Map-reduce** — summarizes chunks independently then combines

## Code Standards

From `.github/copilot-instructions.md`:
- **English only** — all identifiers, comments, commit messages, and error messages must be in English. Flag and correct any Portuguese or other languages.
- **Code smell review** — actively identify and suggest fixes for readability issues, unnecessary complexity, duplication, tight coupling, hidden side effects. Prefer incremental improvements over large rewrites.

## Environment Variables

```
GEMINI_API_KEY=...              # Required for Gemini (default LLM)
OPENAI_API_KEY=...              # Required for OpenAI
GITHUB_TOKEN=...                # Optional; increases GitHub API rate limit
LANGFUSE_PUBLIC_KEY=...         # Optional; enables tracing
LANGFUSE_SECRET_KEY=...
LANGFUSE_BASE_URL=https://us.cloud.langfuse.com
```
