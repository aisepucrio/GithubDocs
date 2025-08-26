from pedro_adapt.agents import GeminiAgent
from pedro_adapt.agent_pipeline import AgentPipeline

import dotenv

import os

dotenv.load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

changelog_agent = GeminiAgent(
    api_key=api_key,
    base_prompt=(
        "Você é um especialista em criar change logs para projetos de software. "
        "Ao receber um diff do git, analise as alterações e gere um change log claro e objetivo, "
        "destacando as principais mudanças, correções de bugs, melhorias e novas funcionalidades. "
        "Organize o change log em tópicos, utilizando uma linguagem acessível e profissional. "
        "Ignore detalhes irrelevantes e foque no impacto das alterações para os usuários e desenvolvedores."
    )
)

formatter_agent = GeminiAgent(
    api_key=api_key,
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

entrada = "Um texto gigantesco que ultrapassa o contexto..."
saida = pipeline.run(entrada)

print("Resultado final:", saida)
