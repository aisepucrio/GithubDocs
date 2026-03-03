# Benchmark

A testing module for GithubDocs that evaluates the AI documentation generation pipeline across multiple configurations. It runs test cases (README creation, README update, Changelog generation), measures execution time, tracks success rates, and exports results to Google Sheets.

## What it does

Each benchmark run:
1. Loads test configurations (from Google Sheets or locally)
2. Runs the GithubDocs pipeline (`src/facade.start`) for each selected config
3. Collects metrics: success, execution time, model, temperature, rendered prompt, output content
4. Exports all results to a Google Sheets spreadsheet (one tab per repository)

## Setup

Create a `.env` file in the **project root** (`githubdocs/.env`) with:

```env
GOOGLE_SHEETS_CREDENTIALS=path/to/credentials.json
GOOGLE_SHEETS_SPREADSHEET_ID=your_spreadsheet_id
```

To get these credentials:
1. Create a project in Google Cloud Console
2. Enable the Google Sheets API
3. Create a Service Account and download the JSON key
4. Share your spreadsheet with the service account email

### Install dependencies

```bash
pip install gspread google-auth python-dotenv
```

## Usage

Run from the **project root** (`githubdocs/`):

```bash
# Test rows 1 to 20 from Google Sheets
python -m benchmark "1-20"

# Test specific rows
python -m benchmark "1,4,7"

# Mix ranges and individual indices
python -m benchmark "1-5,10,15"

# Test all available configs
python -m benchmark "all"
```

### Options

| Flag | Description |
|------|-------------|
| `--list` / `-l` | List all available configs without running |
| `--no-export` | Run tests but skip exporting results to Sheets |
| `--quiet` / `-q` | Suppress verbose output |
| `--local` | Use local configs from `test_configs.py` instead of Google Sheets |
| `--worksheet NAME` / `-w` | Target worksheet name for results export |
| `--credentials PATH` / `-c` | Path to Google credentials JSON |
| `--spreadsheet ID` / `-s` | Google Sheets spreadsheet ID |
| `--config-worksheet NAME` | Name of the worksheet containing test configs (default: `TestConfigs`) |

### Examples

```bash
# List all available test configs
python -m benchmark --list

# Run without exporting to Sheets
python -m benchmark "1-10" --no-export

# Use local fallback configs (no Sheets needed)
python -m benchmark "1" --local

# Export results to a specific worksheet
python -m benchmark "all" --worksheet "MyResults"
```

## Configuring test cases

### Via Google Sheets (default)

Create a worksheet named `TestConfigs` (or set `GOOGLE_SHEETS_CONFIG_WORKSHEET` in `.env`) with these columns:

| Column | Description | Example |
|--------|-------------|---------|
| `description` | Name/label for the test | `EventFlow - Changelog` |
| `repo_path` | Path to the target repository | `external_repos/EventFlow` |
| `branch_name` | Branch to analyse | `main` |
| `commits` | Comma-separated commit SHAs | `abc123, def456` |
| `commit_mixed` | `true` if commits span multiple features | `false` |
| `type` | Test type (see below) | `readme` |
| `model_name` | LLM model to use | `gemini-2.5-flash` |
| `temperature` | Sampling temperature | `0.2` |

**Supported test types:**

| Value | Prompt file | Description |
|-------|-------------|-------------|
| `readme` | `readme.jinja` | Generate a new README from scratch |
| `readme_update` | `readme_update.jinja` | Update an existing README |
| `changelog` | `changelog.jinja` | Generate a changelog from commits |

Rows with an empty `commits` column are skipped automatically.

### Via local configs (fallback)

Edit `test_configs.py` and add TOML config strings to the `TEST_CONFIGS` list and corresponding names to `CONFIG_NAMES`. Then run with `--local`:

```bash
python -m benchmark "1" --local
```

Each TOML string must follow the GithubDocs config format found in conf/config_example.toml

## Output

- Generated files are saved to `output/benchmark_<index>.md`
- Logs are saved to `logs/`
- Results are exported to Google Sheets, grouped by repository name (one tab per repo)
- A `Resumo` (Summary) tab is created with aggregated stats: total tests, successes, failures, success rate, and average execution time broken down by model

## Module structure

| File | Purpose |
|------|---------|
| `__main__.py` | CLI entry point and argument parsing |
| `runner.py` | `BenchmarkRunner` — executes configs and collects `BenchmarkResult` objects |
| `test_configs.py` | Loads configs from Google Sheets or local TOML strings |
| `sheets_exporter.py` | Exports results to Google Sheets |
| `index_parser.py` | Parses index notation (`"1-5,10"` → `[0,1,2,3,4,9]`) |
