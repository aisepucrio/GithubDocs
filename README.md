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

O [git-cliff](https://git-cliff.org/) é uma ferramenta CLI separada e não é instalado via pip/uv. Consulte a documentação oficial para instalá-lo, se necessário.

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

### Linting e Formatação

O [Ruff](https://github.com/astral-sh/ruff) está configurado no arquivo `pyproject.toml` para garantir a qualidade e o estilo do código. O Ruff substitui ferramentas como `flake8`, `black`, `isort`, e `pyupgrade` em uma única ferramenta de alta performance.

```bash
# Verificar problemas de linting
uv run ruff check .

# Formatar código automaticamente
uv run ruff format .
```

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

### Submodules Atuais

A lista de repositórios externos utilizados para documentação é:

  - *(Adicione os repositórios aqui conforme forem incluídos)*

<!-- end list -->

```
```