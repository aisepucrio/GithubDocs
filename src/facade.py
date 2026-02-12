import copy
import os
from .llm_agent import *
from .load_configuration import *
from .repo_info_extraction import *
from .github_integration import IssueTracker
from jinja2 import Environment, FileSystemLoader, meta
from jinja2 import Undefined, make_logging_undefined
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

def print_issues_to_terminal(issues_analysis: dict, issue_tracker: IssueTracker):
    print("\n" + "="*80)
    print("📋 ANÁLISE DE ISSUES DO GITHUB")
    print("="*80)
    
    total = issues_analysis.get('total_issues_referenced', 0)
    if total == 0:
        print("\n⚠️  Nenhuma issue foi referenciada nos commits analisados.")
        print("="*80 + "\n")
        return
    
    print(f"\nTotal de issues encontradas: {total}\n")
    
    issues = issues_analysis.get('issues', {})
    commits_by_issue = issues_analysis.get('commits_by_issue', {})
    
    for issue_num, issue_data in sorted(issues.items()):
        # Cabeçalho da issue
        status_icon = "✅" if issue_data['state'] == 'closed' else "🔴"
        print(f"{status_icon} Issue #{issue_num}: {issue_data['title']}")
        print("-" * 80)
        
        # Informações básicas
        print(f"   Status: {issue_data['state'].upper()}")
        print(f"   Autor: {issue_data['author']}")
        print(f"   Criada em: {issue_data['created_at'][:10]}")
        
        if issue_data.get('closed_at'):
            print(f"   Fechada em: {issue_data['closed_at'][:10]}")
        
        if issue_data.get('labels'):
            labels_str = ', '.join(issue_data['labels'])
            print(f"   Labels: {labels_str}")
        
        if issue_data.get('closing_commit'):
            print(f"   Commit que fechou: {issue_data['closing_commit'][:7]}")
        
        # Descrição
        if issue_data.get('body'):
            body = issue_data['body']
            if len(body) > 200:
                body = body[:200] + "..."
            print(f"\n   Descrição:")
            # Indenta cada linha da descrição
            for line in body.split('\n'):
                if line.strip():
                    print(f"      {line[:76]}")
        
        # Commits relacionados
        related_commits = commits_by_issue.get(issue_num, [])
        if related_commits:
            print(f"\n   Commits relacionados ({len(related_commits)}):")
            for commit in related_commits:
                commit_hash = commit['hash'][:7]
                commit_msg = commit['message'].split('\n')[0][:60]
                print(f"      • {commit_hash} - {commit_msg}")
        
        print("\n")
    
    print("="*80)
    print(f"📊 Resumo: {total} issue(s) analisada(s)")
    print("="*80 + "\n")

def render_prompt(template_path: str, prompt_file: str, variables: dict, repo_path: str, issue_tracker: IssueTracker = None) -> str:
    LoggingUndefined = make_logging_undefined(logger=logger,base=Undefined)
    env = Environment(loader=FileSystemLoader(template_path), undefined=LoggingUndefined)
    # TODO: Its interesting to simplify this with all posibilities in one function only.
    # without that, this function going to have a lot fo env.filters in the future.
    env.filters["read_file"] = lambda rel: load_file(repo_path, rel)
    template = env.get_template(prompt_file)

    return template.render(variables)

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

def build_orchestration_step(orchestration_step: OrchestrationStep, repo_info: list, last_step_output: str | None = None, issue_tracker: IssueTracker = None):
    agent = build_ai_agent(orchestration_step.model_name, temperature = orchestration_step.temperature)
    if agent is None:
        logger.error(f"Agent for model {orchestration_step.model_name} not found.")
        exit(1)

    template_vars = orchestration_step.prompt_variables.copy()
    template_vars['repo_info'] = repo_info
    if last_step_output:
        template_vars['last_step_output'] = last_step_output

    logger.debug(f"Template variables: {template_vars.keys()}")


    prompt = render_prompt(
        orchestration_step.template_path,
        orchestration_step.prompt_file,
        template_vars,
        repo_info["repo_path"],
        issue_tracker
    )

    if agent.need_summarization(prompt):
        logger.error("Prompt still too large after summarization. Consider reducing the number of commits or files.")
        
        
        exit(1)

    response = agent.generate_response_with_prompt(prompt, "")
    return response

def start(base_config: BaseAppConfig, enable_issue_log: bool = False):
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

    issue_tracker = None
    commit_messages = []
    
    if hasattr(base_config.target_info, 'github_token') and base_config.target_info.github_token:
        try:
            repo_name = base_config.target_info.github_repo_name
            issue_tracker = IssueTracker(repo_name, base_config.target_info.github_token)
            
            commit_messages = [commit.get("message", "") for commit in repo_info["commits"]]
            
            from src.llm_agent.github_tools import set_issue_tracker
            set_issue_tracker(issue_tracker, commit_messages)
            
            logger.info(f"✅ GitHub Issues Tools habilitadas para o modelo LLM")
            logger.info(f"   O modelo poderá buscar informações sobre issues autonomamente")
            
            logger.info("Analisando issues mencionadas nos commits...")
            issues_analysis = issue_tracker.analyze_commits(repo_info["commits"])
            logger.info(f"Encontradas {issues_analysis['total_issues_referenced']} issues únicas referenciadas")
            
            if enable_issue_log:
                print_issues_to_terminal(issues_analysis, issue_tracker)
            else:
                repo_info["issues_analysis"] = issues_analysis
        except Exception as e:
            logger.warning(f"Não foi possível inicializar rastreador de issues: {e}")
            logger.warning("Continuando sem análise de issues...")

    final_result = ""
    last_step_output = None
    base_config.orchestration_steps.sort(key=lambda x: x.step)

    for step in base_config.orchestration_steps:
        logger.info(f"Executing step {step.step}: {step.model_name}")
        final_result = build_orchestration_step(step, repo_info, last_step_output, issue_tracker)
        last_step_output = final_result
        
        if final_result is None or final_result.strip() == "":
            logger.info("Final result vazio. Interrompendo o loop.")
            break


    output_path = os.path.join(base_config.output_info.result_path, base_config.output_info.result_file_name)
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(final_result if final_result else "")
        logger.success(f"Documentation generated successfully at {output_path}")
    except IOError as e:
        logger.error(f"Failed to write output file at {output_path}: {e}")
        exit(1)
