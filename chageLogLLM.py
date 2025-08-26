import os
import google.generativeai as genai
import sys
import json

genai.configure(api_key="SUA CHAVE")

model = genai.GenerativeModel('gemini-2.5-flash')

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
response = model.generate_content(prompt)

final_text = response.text  # resultado em texto

# Salvar o changelog final
with open(changelog_final_path, "w", encoding="utf-8") as f:
    f.write(final_text)

print(f"CHANGELOG_FINAL.md gerado com sucesso!")
