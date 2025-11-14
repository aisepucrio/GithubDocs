from src.llm_agent.agent_interface import AIAgent


def read_file(file_path: str)-> str:
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    return content

def summarize_text(text: str, agent: AIAgent) -> str:
    return agent.generate_response("Summarize the following text concisely:", text)

def sumarize_file(file_path: str, agent: AIAgent) -> str:
    content = read_file(file_path)
    return summarize_text(content, agent)