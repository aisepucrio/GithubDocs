from pedro_adapt.agents import GeminiAgent
from pedro_adapt.agent_pipeline import AgentPipeline

import dotenv

import os
from datetime import datetime

dotenv.load_dotenv()

gemini_api_key = os.getenv("GEMINI_API_KEY")
gemini_model_name = "gemini-2.0-flash-lite"

changelog_agent = GeminiAgent(
    api_key=gemini_api_key,
    model_name=gemini_model_name,
    base_prompt=(
        "Você é um especialista em criar change logs para projetos de software. "
        "Ao receber um diff do git, analise as alterações e gere um change log claro e objetivo, "
        "destacando as principais mudanças, correções de bugs, melhorias e novas funcionalidades. "
        "Organize o change log em tópicos, utilizando uma linguagem acessível e profissional. "
        "Ignore detalhes irrelevantes e foque no impacto das alterações para os usuários e desenvolvedores."
    )
)

formatter_agent = GeminiAgent(
    api_key=gemini_api_key,
    model_name=gemini_model_name,
    base_prompt=(
        """
        - **Changelog:** registro em ordem inversa de todas as mudanças (bugs, features, segurança).
        - **Release Notes:** resumo para usuários finais, linguagem simples.
        - **Diferença:** changelog = técnico + completo | release notes = alto nível + não técnico.
        - **Benefícios:** rastrear progresso, transparência, onboarding.
        - **Quando usar:** público técnico, necessidade de detalhes completos.
        - **Formato padrão:**
        - Version (SemVer + data YYYY-MM-DD)
        - Release highlights
        - Added | Changed | Deprecated | Fixed | Security | Breaking changes
        """
    )
)

pipeline = AgentPipeline([changelog_agent, formatter_agent])

with open("base_data/sample.patch", "r") as file:
    entrada = file.read()

saida = pipeline.run(entrada)

output_filename = f"output/result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
with open(output_filename, "w") as file:
    file.write(saida)
