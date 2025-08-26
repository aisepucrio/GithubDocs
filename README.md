# GithubDocs

Este projeto utiliza o [uv](https://github.com/astral-sh/uv), um instalador de pacotes Python ultra rápido e moderno que também inclui o linter/formatter Ruff.

## Instalação do uv

1. Instale o `uv` usando um dos métodos abaixo:

```bash
# Via curl (Linux/macOS)
curl -Ls https://astral.sh/uv/install.sh | bash

# Via pip
pip install uv
```

## Configuração e Uso

### Instalando dependências
Para instalar todas as dependências do projeto:

Inicie uma venv
```bash
uv venv
```
Instale as dependencias
```bash
uv sync
```

### Usando o Ruff para linting e formatação

O Ruff está configurado no arquivo `pyproject.toml`. Para usar:

```bash
# Verificar problemas de linting
uv run ruff check .

# Formatar código automaticamente
uv run ruff format .
```

## Observações
- O `git-cliff` é uma ferramenta CLI separada e não é instalado via pip/uv
- A configuração do Ruff está incluída no arquivo `pyproject.toml`
- O Ruff substituiu ferramentas como flake8, black, isort, pyupgrade, etc., em uma única ferramenta rápida
