import copy
import os
from .llm_agent import *
from .load_configuration import *
from .repo_info_extraction import *
from jinja2 import Environment, FileSystemLoader
from .llm_agent.agents_calls import summarize_text
from .log import CustomLogger
from .llm_agent.context_window_size import LLM_CONTEXT_WINDOWS

AI_DICT = get_agent_dictionary()
logger = CustomLogger()

# MOVER PRA OUTRO LUGAR?
def load_file(repo_path: str, relative_path: str) -> str:
    file_path = os.path.join(repo_path, relative_path)

    if not os.path.exists(file_path):
        return f"Arquivo '{relative_path}' não encontrado"

    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

def render_prompt(template_path: str, prompt_file: str, variables: dict, repo_path: str) -> str:
    env = Environment(loader=FileSystemLoader(template_path))
    env.filters["read_file"] = lambda rel: load_file(repo_path, rel)
    template = env.get_template(prompt_file)
    return template.render(variables)

def populate_template(template_path: str, prompt_file: str, variables: dict, repo_path: str) -> str:
    return render_prompt(template_path, prompt_file, variables, repo_path)

def build_ai_agent(model_name: str, api_key: str = "", base_prompt: str = "", temperature: float = None) -> AIAgent | None:
    agent_class = None
    for key in AI_DICT:
        if key in model_name:
            agent_class = AI_DICT[key]
    if not agent_class and model_name in LLM_CONTEXT_WINDOWS: # Fallback, if there is no direct match, check if the model_name is in the context window dict (ollama models). TODO: improve this
        agent_class = AI_DICT["ollama"]
    if agent_class:
        return agent_class(model_name=model_name, api_key=api_key, base_prompt=base_prompt, temperature=temperature)
    return None

def build_orchestration_step(orchestration_step: OrchestrationStep, repo_info: list, last_step_output: str | None = None):
    agent = build_ai_agent(orchestration_step.model_name, temperature = orchestration_step.temperature)
    if agent is None:
        logger.error(f"Agent for model {orchestration_step.model_name} not found.")
        exit(1)

    template_vars = orchestration_step.prompt_variables.copy()
    template_vars['repo_info'] = repo_info
    if last_step_output:
        template_vars['last_step_output'] = last_step_output

    logger.debug(f"Template variables: {template_vars.keys()}")


    prompt = populate_template(
        orchestration_step.template_path,
        orchestration_step.prompt_file,
        template_vars,
        repo_info["repo_path"]
    )

    # I only summarize the diffs if the prompt is too large without that, probably the code will broke
    # Uncomment this part if needed
    # This is a bit of skill issue of my part, Think on a better way to handle this in the future
    # if agent.need_summarization(prompt):
    #     logger.warning("Prompt exceeds context window size. Summarizing diffs.")
    #     summarized_repo_info = copy.deepcopy(repo_info)
    #     for commit in summarized_repo_info:
    #         for modification in commit['modifications'].values():
    #             if modification['diff']:
    #                 modification['diff'] = summarize_text(modification['diff'], agent)
        
    #     template_vars['repo_info'] = summarized_repo_info
    #     prompt = populate_template(
    #         orchestration_step.template_path,
    #         orchestration_step.prompt_file,
    #         template_vars
    #     )

    if agent.need_summarization(prompt):
        logger.error("Prompt still too large after summarization. Consider reducing the number of commits or files.")
        exit(1)

    response = agent.generate_response_with_prompt(prompt, "")
    return response

def start(base_config: BaseAppConfig):
    try:
        extractor = RepoInfoExtractor(
            repository_path=base_config.target_info.repo_path,
            commit_list=base_config.target_info.commit_list,
            target_branch=base_config.target_info.branch_name,
            ignored_files=base_config.target_info.ignore_files
        )
        repo_info = extractor.extract_repo_info()
    except Exception as e:
        logger.error(f"Failed to extract repository information: {e}")
        exit(1)

    final_result = ""
    last_step_output = None
    base_config.orchestration_steps.sort(key=lambda x: x.step)

    for step in base_config.orchestration_steps:
        logger.info(f"Executing step {step.step}: {step.model_name}")
        final_result = build_orchestration_step(step, repo_info, last_step_output)
        last_step_output = final_result

    output_path = os.path.join(base_config.output_info.result_path, base_config.output_info.result_file_name)
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(final_result if final_result else "")
        logger.success(f"Documentation generated successfully at {output_path}")
    except IOError as e:
        logger.error(f"Failed to write output file at {output_path}: {e}")
        exit(1)
