"""
Arquivo de configurações de teste para benchmark.

COMO USAR:
    1. Cole suas configs TOML como strings no array TEST_CONFIGS abaixo
    2. Cada config é uma string com o conteúdo TOML completo
    3. Dê um nome descritivo para cada config no array CONFIG_NAMES

EXEMPLO:
    TEST_CONFIGS = [
        '''
        [target_information]
        repo_path = "external_repos/MyRepo"
        ...
        ''',
        '''
        [target_information]
        repo_path = "external_repos/OtherRepo"
        ...
        ''',
    ]

    CONFIG_NAMES = [
        "MyRepo - Gemini Flash",
        "OtherRepo - GPT-4",
    ]
"""

# Cole suas configs TOML aqui como strings
TEST_CONFIGS: list[str] = [
    # Config 1 - Exemplo
    '''
[target_information]
repo_path = "external_repos/EventFlow"
branch_name = "develop-v1"
commit_list = ["6bcade563d627ea3d2b35f59d4d5dee56d6ea6a"]
ignore_files = ["README.md", "CHANGELOG.md"]

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
prompt_file = "changelog.jinja"
prompt_variables = { name = "Benchmark Test 1", repo = "external_repos/EventFlow" }
''',

    # Config 2 - Exemplo com temperatura diferente
    '''
[target_information]
repo_path = "external_repos/EventFlow"
branch_name = "develop-v1"
commit_list = ["6bcade563d627ea3d2b35f59d4d5dee56d6ea6a"]
ignore_files = ["README.md", "CHANGELOG.md"]

[agents]

[[agents.output]]
result_path = "output/"
log_path = "logs/"
result_file_name = "benchmark_test_2.md"

[[agents.orchestration]]
step = 1
model_name = "gemini-2.5-flash-lite"
temperature = 0.8
template_path = "prompt/"
prompt_file = "changelog.jinja"
prompt_variables = { name = "Benchmark Test 2", repo = "external_repos/EventFlow" }
''',

    # Adicione mais configs aqui...
]

# Nomes descritivos para cada config (opcional, mas recomendado)
# Se vazio, será usado "Config 1", "Config 2", etc.
CONFIG_NAMES: list[str] = [
    "EventFlow - Temp 0.2",
    "EventFlow - Temp 0.8",
    # Adicione mais nomes aqui...
]


def get_config_name(index: int) -> str:
    """Retorna o nome da config pelo índice (0-based)."""
    if index < len(CONFIG_NAMES) and CONFIG_NAMES[index]:
        return CONFIG_NAMES[index]
    return f"Config {index + 1}"


def get_total_configs() -> int:
    """Retorna o número total de configs disponíveis."""
    return len(TEST_CONFIGS)
