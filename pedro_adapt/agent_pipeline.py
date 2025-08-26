# agent_pipeline.py
from typing import List
from ai_agent import AIAgent

# agent_pipeline.py
from typing import List
from ai_agent import AIAgent

class AgentPipeline:
    def __init__(self, agents: List[AIAgent]):
        self.agents = agents

    def _summarize_until_fits(self, agent: AIAgent, text: str) -> str:
        """Aplica sumarização iterativa até o texto caber no contexto do modelo."""
        while agent.need_summarization(text):
            text = agent.generate_response("Summarize the following text:\n" + text)
        return text

    def run(self, input: str) -> str:
        current_text = input

        for agent in self.agents:
            # Garante que o input caiba na janela de contexto
            current_text = self._summarize_until_fits(agent, current_text)

            # Executa o processamento principal do agente
            current_text = agent.generate_response(current_text)

        return current_text
