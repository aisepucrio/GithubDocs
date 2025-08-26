import os
import google.generativeai as genai
import sys
import json
import subprocess
from dotenv import load_dotenv

def obter_commit():
    cmd = ["git", "log", "-n", "1", "--pretty=format:%H", "--", "README.md"]

    resultado = subprocess.run(cmd, capture_output=True, text=True, check=True)

    return resultado.stdout.strip()

def gerar_changelog(hash):
    init_cmd = ["git-cliff", "--init"]
    subprocess.run(init_cmd, capture_output=True, text=True)

    # gera o changelog
    cmd = [
        "git-cliff",
        f"{hash}..HEAD",
        "-o",
        "CHANGELOG.md"
    ]

    resultado = subprocess.run(cmd, capture_output=True, text=True)

    if resultado.returncode == 0:
        print("CHANGELOG.md gerado com sucesso!")
    else:
        print("Erro ao gerar CHANGELOG:")
        print(resultado.stderr)
hash = obter_commit()

gerar_changelog(hash)

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

# Caminhos dos arquivos
changelog_raw_path = "CHANGELOG.md"
changelog_final_path = "CHANGELOG_FINAL.md"

# Ler o changelog bruto
with open(changelog_raw_path, "r", encoding="utf-8") as f:
    raw_text = f.read()

# Prompt para a LLM
prompt = f"""
Você é um assistente de documentação de software.
Transforme o seguinte changelog em português, no padrão Good Docs:

- Adicione as seções: Version, Release highlights, Added, Changed, Deprecated, Fixed, Security, Breaking changes
- Faça um resumo curto das mudanças importantes em Release highlights
- Organize os commits corretamente nas seções
- Melhore a clareza e a linguagem formal
- Mantenha a versão e a data conforme SemVer + YYYY-MM-DD

Changelog bruto:
{raw_text}
"""

# Gerar o changelog final
resposta = genai.GenerativeModel("gemini-2.0-flash-lite").generate_content(prompt)

final_text = resposta.text  # resultado em texto

# Salvar o changelog final
with open(changelog_final_path, "w", encoding="utf-8") as f:
    f.write(final_text)

print(f"CHANGELOG_FINAL.md gerado com sucesso!")

def ler_arquivo(caminho):
    with open(caminho, "r", encoding="utf-8") as f:
        return f.read()

def salvar_arquivo(caminho, conteudo):
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(conteudo)

changelog = ler_arquivo("CHANGELOG_FINAL.md")
readme = ler_arquivo("README.md")

prompt = f"""
Você é um assistente que cria arquivos README em Markdown para projetos de software.

Aqui está o CHANGELOG do projeto:
{changelog}

Aqui está o README atual:
{readme}

Crie um novo README em Markdown atualizado, integrando todas as informações relevantes do changelog.  
Mantenha exatamente as mesmas seções e o mesmo formato. Só faça alterações necessárias de acordo com as mudanças do changelog. Não crie uma seção chamda changelog. Não crie novas seções em nenhuma hipótese.
Forneça o conteúdo completo do README pronto para salvar em arquivo .md. Não explique nada, apenas gere o Markdown.
"""

resposta = genai.GenerativeModel("gemini-2.0-flash-lite").generate_content(prompt)

salvar_arquivo("README_UPDATED.md", resposta.text)

print("Novo README gerado em README_UPDATED.md")
import os
import google.generativeai as genai
import subprocess
from dotenv import load_dotenv

def obter_commit():
    cmd = ["git", "log", "-n", "1", "--pretty=format:%H", "--", "README.md"]

    resultado = subprocess.run(cmd, capture_output=True, text=True, check=True)

    return resultado.stdout.strip()

def gerar_changelog(hash):
    init_cmd = ["git-cliff", "--init"]
    subprocess.run(init_cmd, capture_output=True, text=True)

    # gera o changelog
    cmd = [
        "git-cliff",
        f"{hash}..HEAD",
        "-o",
        "CHANGELOG.md"
    ]

    resultado = subprocess.run(cmd, capture_output=True, text=True)

    if resultado.returncode == 0:
        print("CHANGELOG.md gerado com sucesso!")
    else:
        print("Erro ao gerar CHANGELOG:")
        print(resultado.stderr)
hash = obter_commit()

gerar_changelog(hash)

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

def ler_arquivo(caminho):
    with open(caminho, "r", encoding="utf-8") as f:
        return f.read()

def salvar_arquivo(caminho, conteudo):
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(conteudo)

changelog = ler_arquivo("CHANGELOG.md")
readme = ler_arquivo("README.md")

prompt = f"""
Você é um assistente que cria arquivos README em Markdown para projetos de software.

Aqui está o CHANGELOG do projeto:
{changelog}

Aqui está o README atual:
{readme}

Crie um novo README em Markdown atualizado, integrando todas as informações relevantes do changelog.  
Mantenha exatamente as mesmas seções e o mesmo formato. Só faça alterações necessárias de acordo com as mudanças do changelog. Não crie uma seção chamda changelog. Não crie novas seções em nenhuma hipótese.
Forneça o conteúdo completo do README pronto para salvar em arquivo .md. Não explique nada, apenas gere o Markdown.
"""

resposta = genai.GenerativeModel("gemini-2.0-flash-lite").generate_content(prompt)

salvar_arquivo("README_UPDATED.md", resposta.text)

print("Novo README gerado em README_UPDATED.md")