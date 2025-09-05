from src.llm_agent.agents import GeminiAgent
from src.llm_agent.agent_pipeline import AgentPipeline
from utils.tree import tree

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


readme_agent = GeminiAgent(
    api_key=gemini_api_key,
    model_name=gemini_model_name,
    base_prompt=(
        """    You are an assistant that generates README.md files based on the given file tree.
        
        INSTRUCTIONS:
        - Only include sections if there is evidence in the file tree that they apply.
        - Do NOT invent content — base everything on the provided tree.
        - Output only the README.md content.
        - Use dependencies to know how to install correctly based on tree
        - maing file structure should be based on tree
        
        README TEMPLATE:
        # GithubDocs

        # Main File Structure 

        # describe technology and main language used

        # Installation

        # License
        """
    )
)



# pipeline = AgentPipeline([changelog_agent, formatter_agent])

# with open("base_data/sample.patch", "r") as file:
#     entrada = file.read()

# saida = pipeline.run(entrada)

# output_filename = f"output/result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
# with open(output_filename, "w") as file:
#     file.write(saida)

# ==================================

pipeline_readme = AgentPipeline([readme_agent])

tree = tree()
print(tree)

print("\n\nGerando README.md com base na estrutura de diretórios...")

saidaReadme = pipeline_readme.run(tree)

output_readme = f"output/readme{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
with open(output_readme, "w") as file:
    file.write(saidaReadme)