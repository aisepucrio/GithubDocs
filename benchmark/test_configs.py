"""
Arquivo de configurações de teste para benchmark.

MODOS DE USO:
    1. MANUAL: Cole configs TOML como strings no array TEST_CONFIGS
    2. GOOGLE SHEETS: Use fetch_configs_from_sheets() para carregar do Sheets

CAMPOS DO GOOGLE SHEETS:
    - ini_commit: Commit inicial do range
    - end_commit: Commit final do range
    - branch_name: Nome da branch
    - commit_mixed: Se True, usa range de commits
    - type: Tipo do teste (README_CREATE, README_UPDATE, CHANGELOG)
    - description: Descrição/nome do teste
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional
import os

# Diretório base do benchmark para resolver caminhos relativos
BENCHMARK_DIR = Path(__file__).parent

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False


class TestType(Enum):
    """Tipos de teste suportados."""
    README_CREATE = "readme"
    README_UPDATE = "readme_update"
    CHANGELOG = "changelog"


@dataclass
class TestConfigRow:
    """Representa uma linha de configuração do Google Sheets."""
    repo_path: str
    commits: str
    branch_name: str
    commit_mixed: bool
    test_type: TestType
    description: str

    # Campos opcionais com defaults
    model_name: str = "gemini-2.5-flash-lite"
    temperature: float = 0.2
    project_description: str = ""

    @classmethod
    def from_sheet_row(cls, row: dict) -> "TestConfigRow":
        """Cria instância a partir de uma linha do Sheets."""
        return cls(
            commits=row.get("commits", ""),
            branch_name=row.get("branch_name", "main"),
            commit_mixed=str(row.get("commit_mixed", "")).lower() in ("true", "1", "yes", "sim","y"),
            test_type=TestType(row.get("type", "readme")),
            description=row.get("description", ""),
            repo_path=row.get("repo_path", "external_repos/EventFlow"),
            model_name=(row.get("model_name", "gemini-2.5-flash")) or "gemini-2.5-flash",
            temperature=float(row.get("temperature", 0.2) or 0.2),
            project_description=row.get("project_description", ""),
        )


# Mapeamento de tipo de teste para prompt file
TEST_TYPE_PROMPTS = {
    TestType.README_CREATE: "readme.jinja",
    TestType.README_UPDATE: "readme_update.jinja",
    TestType.CHANGELOG: "changelog.jinja",
}

def _sanitize_toml_string(value: str) -> str:
    """Sanitiza uma string para uso em TOML."""
    # Remove quebras de linha e espaços extras
    value = " ".join(value.split())
    # Escapa barras invertidas primeiro, depois aspas duplas
    value = value.replace("\\", "\\\\").replace('"', '\\"')
    return value


def build_config_toml(row: TestConfigRow, index: int) -> str:
    """
    Constrói uma string TOML a partir de uma TestConfigRow.

    Args:
        row: Dados da configuração
        index: Índice do teste (para nome do arquivo output)

    Returns:
        String TOML válida
    """
    print("commits : ", row.commits)

    commits_str = _build_commit_list(row.commits)

    if not row.commits: 
        raise ValueError("Lista de commits vazia na configuração")
    prompt_file = TEST_TYPE_PROMPTS.get(row.test_type, "changelog.jinja")

    safe_desc = _sanitize_toml_string(row.description)
    safe_repo = _sanitize_toml_string(row.repo_path)
    safe_branch = _sanitize_toml_string(row.branch_name)
    safe_model = _sanitize_toml_string(row.model_name)
    safe_project_description = _sanitize_toml_string(row.project_description)

    prompt_variables = f'{{ name = "{safe_desc}", repo = "{safe_repo}"'
    if row.test_type == TestType.README_CREATE and safe_project_description:
        prompt_variables += f', repo_description = "{safe_project_description}"'
    prompt_variables += ' }'

    conf = f'''[target_information]
    repo_path = "{safe_repo}"
    branch_name = "{safe_branch}"
    commit_list = [{commits_str}]
    ignore_files = ["IGNORED_PRESET", "RELEASE_NOTES.md","CHANGELOG.md","README.md"]

    [agents]

    [[agents.output]]
    result_path = "output/"
    log_path = "logs/"
    result_file_name = "benchmark_{index}.md"

    [[agents.orchestration]]
    step = 1
    model_name = "{safe_model}"
    temperature = {row.temperature}
    template_path = "prompt/"
    prompt_file = "{prompt_file}"
    prompt_variables = {prompt_variables}
    tools = []
    '''

    print(conf)

    return conf

def _build_commit_list(commits: str) -> str:
    """Converte string de commits separados por vírgula em string TOML de lista."""
    cmts = commits.split(",")
    quoted = [f'"{c.strip()}"' for c in cmts if c.strip()]
    return ", ".join(quoted)


@dataclass
class ConfigMetadata:
    """Metadados de uma configuração de teste."""
    description: str = ""
    commit_mixed: bool = False


def fetch_configs_from_sheets(
    worksheet_name: str = "TestConfigs",
    credentials_path: Optional[str] = None,
    spreadsheet_id: Optional[str] = None,
) -> tuple[list[str], list[str], list[ConfigMetadata]]:
    """
    Busca configurações de teste do Google Sheets.

    Args:
        worksheet_name: Nome da aba com as configs
        credentials_path: Caminho para credenciais (ou via env)
        spreadsheet_id: ID da planilha (ou via env)

    Returns:
        Tupla (TEST_CONFIGS, CONFIG_NAMES, CONFIG_METADATA)
    """
    if not GSPREAD_AVAILABLE:
        raise ImportError(
            "gspread não instalado. Execute: pip install gspread google-auth"
        )

    creds_path = credentials_path or os.getenv("GOOGLE_SHEETS_CREDENTIALS")
    # Resolve caminhos relativos baseado no diretório do benchmark
    if creds_path and not Path(creds_path).is_absolute():
        creds_path = str(BENCHMARK_DIR / creds_path)
    sheet_id = spreadsheet_id or os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID")

    if not creds_path or not sheet_id:
        raise ValueError(
            "Configure GOOGLE_SHEETS_CREDENTIALS e GOOGLE_SHEETS_SPREADSHEET_ID"
        )

    credentials = Credentials.from_service_account_file(
        creds_path,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets.readonly",
            "https://www.googleapis.com/auth/drive.readonly",
        ],
    )
    client = gspread.authorize(credentials)
    spreadsheet = client.open_by_key(sheet_id)
    worksheet = spreadsheet.worksheet(worksheet_name)

    # Pega todas as linhas como dicts (primeira linha = headers)
    records = worksheet.get_all_records()

    configs: list[str] = []
    names: list[str] = []
    metadata: list[ConfigMetadata] = []

    for i, record in enumerate(records, start=1):
        if not record.get("commits"):
            print(f"Aviso: Teste de índice {i} ignorada por não ter commits definidos.")
            continue
        row = TestConfigRow.from_sheet_row(record)
        config_toml = build_config_toml(row, i)
        configs.append(config_toml)
        names.append(row.description or f"Test {i}")
        metadata.append(ConfigMetadata(
            description=row.description,
            commit_mixed=row.commit_mixed,
        ))

    return configs, names, metadata


def load_configs(from_sheets: bool = False, **sheets_kwargs) -> tuple[list[str], list[str], list[ConfigMetadata]]:
    """
    Carrega configs do Sheets ou usa as manuais.

    Args:
        from_sheets: Se True, busca do Google Sheets
        **sheets_kwargs: Argumentos para fetch_configs_from_sheets

    Returns:
        Tupla (TEST_CONFIGS, CONFIG_NAMES, CONFIG_METADATA)
    """
    if from_sheets:
        return fetch_configs_from_sheets(**sheets_kwargs)

    # Metadados padrão para configs locais
    metadata = [ConfigMetadata(description=name) for name in CONFIG_NAMES]
    return TEST_CONFIGS, CONFIG_NAMES, metadata


# ============================================================================
# CONFIGS MANUAIS (fallback quando não usa Sheets)
# ============================================================================

TEST_CONFIGS: list[str] = [
    '''
[target_information]
repo_path = "external_repos/EventFlow"
branch_name = "develop-v1"
commit_list = ["621a25d273434b7f371bef60b7e1d558f7bb3f06"]
ignore_files = ["README.md", "CHANGELOG.md", "IGNORED_PRESET"]

[agents]

[[agents.output]]
result_path = "output/"
log_path = "logs/"
result_file_name = "benchmark_test_1.md"

[[agents.orchestration]]
step = 1
model_name = "gemini-2.5-flash-lite"
temperature = 0.2
template_path = "prompt/"
prompt_file = "changelog/changelog.jinja"
prompt_variables = { name = "EventFlow - Changelog", repo = "external_repos/EventFlow" }
tools = []
''',
    '''
[target_information]
repo_path = "external_repos/lm4smells-core"
branch_name = "main"
commit_list = ["7ef69d178f2413692df590159b9b07f930306bd5"]
ignore_files = ["README.md", "IGNORED_PRESET"]

[agents]

[[agents.output]]
result_path = "output/"
log_path = "logs/"
result_file_name = "benchmark_test_2.md"

[[agents.orchestration]]
step = 1
model_name = "gemini-2.5-flash-lite"
temperature = 0.2
template_path = "prompt/"
prompt_file = "readme-update/readme_update.jinja"
prompt_variables = { name = "lm4smells-core - README Update", repo = "external_repos/lm4smells-core" }
tools = []
''',
    '''
[target_information]
repo_path = "external_repos/flask"
branch_name = "main"
commit_list = ["4cae5d8e411b1e69949d8fae669afeacbd3e5908"]
ignore_files = ["README.md", "CHANGELOG.md", "IGNORED_PRESET"]

[agents]

[[agents.output]]
result_path = "output/"
log_path = "logs/"
result_file_name = "benchmark_test_3.md"

[[agents.orchestration]]
step = 1
model_name = "gemini-2.5-flash-lite"
temperature = 0.2
template_path = "prompt/"
prompt_file = "changelog/changelog.jinja"
prompt_variables = { name = "Flask - Changelog", repo = "external_repos/flask" }
tools = []
''',
]

CONFIG_NAMES: list[str] = [
    "EventFlow - Changelog",
    "lm4smells-core - README Update",
    "Flask - Changelog",
]

def get_config_name(index: int) -> str:
    """Retorna o nome da config pelo índice (0-based)."""
    if index < len(CONFIG_NAMES) and CONFIG_NAMES[index]:
        return CONFIG_NAMES[index]
    return f"Config {index + 1}"


def get_total_configs() -> int:
    """Retorna o número total de configs disponíveis."""
    return len(TEST_CONFIGS)