from .conf_structures import Orchestration, LLM


def check_conf_orchestration(orchestration: Orchestration, agents: LLM):
    orchestration_steps = orchestration.flow
    for step in orchestration_steps:
        agent = agents.providers.get(step.from_step)
        if not agent:
            print(f"Agent {step.from_step} not found.")