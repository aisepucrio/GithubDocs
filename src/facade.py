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
from .llm_agent.github_tools import get_github_issue_tools
from langgraph.checkpoint.memory import InMemorySaver



AI_DICT = get_agent_dictionary()
logger = CustomLogger()
RUNNABLE_CONFIG = {"configurable": {"thread_id": "current-run"}}

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

def refine_oversized_modifications(repo_info: dict, agent: AIAgent, per_file_budget: int) -> dict:
    """Refina diffs e source_code_before que excedem per_file_budget tokens.

    Retorna um deep copy de repo_info com os campos refinados via refine_content.
    """
    refined = copy.deepcopy(repo_info)
    for commit in refined.get("commits", []):
        for mod in commit.get("modifications", {}).values():
            content = (mod.get("diff") or "") + (mod.get("source_code_before") or "")
            if agent._count_tokens(content) > per_file_budget:
                if mod.get("diff"):
                    mod["diff"] = agent.refine_content(mod["diff"])
                if mod.get("source_code_before"):
                    mod["source_code_before"] = agent.refine_content(mod["source_code_before"])
    return refined

REDUCE_PROMPT_MAP = {
    "changelog.jinja": "reduce_changelog.jinja",
    "readme_update.jinja": "reduce_readme_update.jinja",
    "readme.jinja": "reduce_readme.jinja",
}

def map_reduce_step(repo_info: dict, agent: AIAgent, orchestration_step: OrchestrationStep, template_vars: dict) -> str:
    """Aplica map-reduce: summariza cada arquivo via batch, depois reduz com o prompt específico."""

    OPTIONALS_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "..", "prompt", "optionals")
    MAP_PROMPT_FILE = "map.jinja"

    reduce_file = REDUCE_PROMPT_MAP.get(orchestration_step.prompt_file)
    if not reduce_file:
        logger.warning(f"Map-reduce: no reduce prompt mapped for '{orchestration_step.prompt_file}'. Using generic reduce.jinja.")
        reduce_file = "reduce.jinja"

    all_files = []
    for commit in repo_info.get("commits", []):
        for file_path, modification in commit.get("modifications", {}).items():
            all_files.append((file_path, modification))

    if not all_files:
        logger.warning("Map-reduce: no modifications found.")
        return ""

    # Map phase: render a map prompt per file, then batch all at once
    env = Environment(loader=FileSystemLoader(OPTIONALS_TEMPLATE_PATH))
    map_template = env.get_template(MAP_PROMPT_FILE)

    map_prompts = [
        map_template.render(file_path=file_path, modification=modification)
        for file_path, modification in all_files
    ]

    logger.info(f"Map-reduce: sending {len(map_prompts)} files in batch...")
    map_responses = agent.chat_model.batch(map_prompts)
    map_summaries = [r.content for r in map_responses]

    logger.info(f"Map-reduce: map phase done. {len(map_summaries)} summaries generated.")

    # Reduce phase: use the specific reduce prompt with repo_info (without diffs) + map summaries
    reduce_template = env.get_template(reduce_file)
    reduce_prompt = reduce_template.render(
        map_summaries=map_summaries,
        **template_vars
    )

    config = {"configurable": {"thread_id": f"step-{orchestration_step.step}-reduce"}}
    return agent.generate_response_with_prompt(reduce_prompt, "", config=config)


TOOL_CALLING_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "..", "prompt", "tool-calling")

TOOL_CALLING_PROMPT_MAP = {
    "readme.jinja": "tool_calling_readme.jinja",
    "changelog.jinja": "tool_calling_changelog.jinja",
    "readme_update.jinja": "tool_calling_readme_update.jinja",
}


def _resolve_tool_calling_prompt(prompt_file: str) -> str:
    # Aceita tanto "readme.jinja" quanto "readme/readme.jinja" — o benchmark
    # usa caminhos prefixados (TEST_TYPE_PROMPTS), então normalizamos pelo basename.
    key = os.path.basename(prompt_file)
    if key not in TOOL_CALLING_PROMPT_MAP:
        raise ValueError(
            f"--tool-calling: prompt_file '{prompt_file}' tem nenhum equivalente em prompt/tool-calling/. "
            f"Suportados: {list(TOOL_CALLING_PROMPT_MAP.keys())}."
        )
    return TOOL_CALLING_PROMPT_MAP[key]


from langchain_core.callbacks import BaseCallbackHandler


class _ToolCallLogger(BaseCallbackHandler):
    """Callback handler que loga toda chamada de tool feita pela LLM."""

    _MAX_OUTPUT_CHARS = 300
    _MAX_INPUT_CHARS = 200

    def _short(self, s, limit: int) -> str:
        s = str(s)
        if len(s) <= limit:
            return s
        return f"{s[:limit]}... [+{len(s) - limit} chars]"

    def on_tool_start(self, serialized, input_str, **kwargs):
        name = (serialized or {}).get("name", "<unknown>")
        inputs = kwargs.get("inputs")
        if isinstance(inputs, dict):
            args_str = ", ".join(f"{k}={self._short(v, self._MAX_INPUT_CHARS)}" for k, v in inputs.items())
        else:
            args_str = self._short(input_str, self._MAX_INPUT_CHARS)
        logger.info(f"🔧 [tool] {name}({args_str})")

    def on_tool_end(self, output, **kwargs):
        text = getattr(output, "content", None) if not isinstance(output, (str, bytes)) else output
        if text is None:
            text = output
        logger.info(f"✅ [tool] -> {self._short(text, self._MAX_OUTPUT_CHARS)}")

    def on_tool_error(self, error, **kwargs):
        logger.warning(f"❌ [tool] error: {error}")


def execute_tool_calling_step(
    extractor: "RepoInfoExtractor",
    orchestration_step: OrchestrationStep,
    last_output: str | None,
    context_memory: InMemorySaver,
) -> str:
    """Executa uma step em modo --tool-calling: prompt enxuto + tools do extractor.

    O LLM puxa dados do repo sob demanda em vez de receber tudo no prompt.
    """
    agent = build_ai_agent(
        orchestration_step.model_name,
        temperature=orchestration_step.temperature,
        context_memory=context_memory,
    )
    if agent is None:
        raise ValueError(f"--tool-calling: modelo '{orchestration_step.model_name}' nao suportado.")

    tools = list(extractor.as_tools())
    issue_tools = get_github_issue_tools()
    if issue_tools:
        tools.extend(issue_tools)

    prompt_file = _resolve_tool_calling_prompt(orchestration_step.prompt_file)
    template_vars = {"prompt_variables": orchestration_step.prompt_variables}
    if last_output:
        template_vars["last_step_output"] = last_output

    prompt = render_prompt(
        TOOL_CALLING_TEMPLATE_PATH,
        prompt_file,
        template_vars,
        extractor.repository_path,
    )

    logger.info(
        f"--tool-calling step {orchestration_step.step}: model={orchestration_step.model_name}, "
        f"tools={len(tools)} (extractor={len(extractor.as_tools())} + issue={len(issue_tools)})"
    )

    config = {
        "configurable": {"thread_id": f"step-{orchestration_step.step}"},
        "callbacks": [_ToolCallLogger()],
    }
    return agent.invoke_with_tools(prompt, tools, config=config)


def build_ai_agent(model_name: str, api_key: str = "", base_prompt: str = "", temperature: float = None, context_memory:InMemorySaver = None) -> AIAgent | None:
    agent_class = None
    for key in AI_DICT:
        if key in model_name:
            agent_class = AI_DICT[key]
    if not agent_class and model_name in LLM_CONTEXT_WINDOWS: # Fallback, if there is no direct match, check if the model_name is in the context window dict (ollama models). TODO: improve this
        agent_class = AI_DICT["ollama"]
    if agent_class:
        return agent_class(model_name=model_name, api_key=api_key, base_prompt=base_prompt, temperature=temperature, context_memory=context_memory)
    return None

def build_orchestration_step(orchestration_step: OrchestrationStep, repo_info: list, last_step_output: str | None = None, issue_tracker: IssueTracker = None, context_memory:InMemorySaver = None, config: dict = None):
    agent = build_ai_agent(orchestration_step.model_name, temperature = orchestration_step.temperature, context_memory=context_memory)
    if agent is None:
        error = ValueError(f"Agent for model {orchestration_step.model_name} not found.")
        logger.error(str(error))
        raise error

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
        error = RuntimeError("Prompt still too large after summarization. Consider reducing the number of commits or files.")
        logger.error(str(error))
        raise error

    response = agent.generate_response_with_prompt(prompt, "", config=config)
    return response

def create_step_chain(orchestration_step: OrchestrationStep, repo_info: dict, context_memory: InMemorySaver, cli_params: "CliParams" = None, extractor: "RepoInfoExtractor" = None):
    """Cria uma função para executar uma step específica"""


    def execute_step(last_output: str) -> str:
        logger.info(f"Executing step {orchestration_step.step}: {orchestration_step.model_name}")

        if cli_params and cli_params.tool_calling:
            if extractor is None:
                raise RuntimeError("--tool-calling exige um RepoInfoExtractor mas nenhum foi passado para a chain.")
            return execute_tool_calling_step(extractor, orchestration_step, last_output, context_memory)

        # Instancia o agente
        agent = build_ai_agent(
            orchestration_step.model_name,
            temperature=orchestration_step.temperature,
            context_memory=context_memory,
        )

        if agent is None:
            error = ValueError(f"Agent for model {orchestration_step.model_name} not found.")
            logger.error(str(error))
            raise error
            

        # Prepara as variáveis do template
        template_vars = orchestration_step.prompt_variables.copy()
        template_vars['repo_info'] = repo_info
        #TODO acredito que com a implementação do langchain esse last_output é obsoleto...
        if last_output:
            template_vars['last_step_output'] = last_output

        logger.debug(f"Template variables: {template_vars.keys()}")

        # Renderiza o prompt
        prompt = render_prompt(
            orchestration_step.template_path,
            orchestration_step.prompt_file,
            template_vars,
            repo_info["repo_path"]
        )

        # Se --refine ativo e prompt excede janela, refina modificações antes de reenviar
        if cli_params and cli_params.refine and agent.need_summarization(prompt):
            logger.info("Prompt excede janela de contexto. Aplicando refine nas modificações...")
            per_file_budget = agent._get_model_window_context() // 4
            refined_repo_info = refine_oversized_modifications(repo_info, agent, per_file_budget)
            template_vars['repo_info'] = refined_repo_info
            prompt = render_prompt(
                orchestration_step.template_path,
                orchestration_step.prompt_file,
                template_vars,
                repo_info["repo_path"]
            )

        if cli_params and cli_params.map_reduce:
            logger.info("Map-Reduce mode active. Summarizing each file in batch...")
            effective_repo_info = template_vars.get('repo_info', repo_info)
            return map_reduce_step(effective_repo_info, agent, orchestration_step, template_vars)

        if agent.need_summarization(prompt):
            error = RuntimeError("Prompt too large for model context window. try enabling --refine or --map_reduce, or reduce the number of commits/files.")
            logger.error(str(error))
            raise error

        config = {"configurable": {"thread_id": f"step-{orchestration_step.step}"}}
        response = agent.generate_response_with_prompt(prompt, "", config=config)


        return response


    return execute_step

def build_chain(orchestration_steps: list[OrchestrationStep], repo_info: dict, context_memory: InMemorySaver, cli_params: "CliParams" = None, extractor: "RepoInfoExtractor" = None):
    """Encadeia as steps usando composição de funções"""


    # Ordena as steps
    sorted_steps = sorted(orchestration_steps, key=lambda x: x.step)


    # Cria as funções para cada step
    step_functions = [
        create_step_chain(step, repo_info, context_memory, cli_params=cli_params, extractor=extractor)
        for step in sorted_steps
    ]
    
    def execute_chain(initial_input: str = "") -> str:
        """Executa a cadeia de steps sequencialmente"""
        result = initial_input
        
        for step_func in step_functions:
            result = step_func(result)
            print(result)
            # Para se o resultado estiver vazio
            if result is None or result.strip() == "":
                logger.info("Result vazio. Interrompendo a chain.")
                break
        
        return result
    
    return execute_chain

def start(base_config: BaseAppConfig):
    tool_calling_mode = bool(base_config.cli_params and base_config.cli_params.tool_calling)
    try:
        extractor = RepoInfoExtractor(
            repository_path=base_config.target_info.repo_path,
            commit_list=base_config.target_info.commit_list,
            target_branch=base_config.target_info.branch_name,
            ignored_files=base_config.target_info.ignore_files
        )
        repo_info = None if tool_calling_mode else extractor.extract_repo_info()
    except Exception as e:
        logger.error(f"Failed to extract repository information: {e}")
        raise

    issue_tracker = None

    github_token = os.getenv('GITHUB_TOKEN')
    if github_token and hasattr(base_config.target_info, 'github_repo_name') and base_config.target_info.github_repo_name:
        try:
            repo_name = base_config.target_info.github_repo_name
            issue_tracker = IssueTracker(repo_name, github_token)

            if tool_calling_mode:
                summaries = extractor._list_commits_objs()
                commit_messages = [s.message for s in summaries]
                commits_for_analysis = [{"hash": s.hash, "message": s.message} for s in summaries]
            else:
                commit_messages = [commit.get("message", "") for commit in repo_info["commits"]]
                commits_for_analysis = repo_info["commits"]

            from src.llm_agent.github_tools import set_issue_tracker
            set_issue_tracker(issue_tracker, commit_messages)

            logger.info(f"✅ GitHub Issues Tools habilitadas para o modelo LLM")
            logger.info(f"   O modelo poderá buscar informações sobre issues autonomamente")

            # Em modo --tool-calling, só rodamos a análise eager se o usuário pediu --issuelog
            # (LLM puxa info de issues sob demanda via tools).
            if tool_calling_mode and not base_config.cli_params.enable_issue_log:
                logger.info("--tool-calling: pulando analyze_commits eager. Issues acessíveis via tools.")
            else:
                logger.info("Analisando issues mencionadas nos commits...")
                issues_analysis = issue_tracker.analyze_commits(commits_for_analysis)
                logger.info(f"Encontradas {issues_analysis['total_issues_referenced']} issues únicas referenciadas")

                if base_config.cli_params.enable_issue_log:
                    print_issues_to_terminal(issues_analysis, issue_tracker)
                elif not tool_calling_mode:
                    repo_info["issues_analysis"] = issues_analysis
        except Exception as e:
            logger.warning(f"Não foi possível inicializar rastreador de issues: {e}")
            logger.warning("Continuando sem análise de issues...")

    final_result = ""
    last_step_output = None
    base_config.orchestration_steps.sort(key=lambda x: x.step)

    context_memory = InMemorySaver()

    # criação da orquestração anterior
    # for step in base_config.orchestration_steps:
    #     logger.info(f"Executing step {step.step}: {step.model_name}")
    #     final_result = build_orchestration_step(step, repo_info, last_step_output, issue_tracker, context_memory, RUNNABLE_CONFIG)
    #     last_step_output = final_result
        
    #     if final_result is None or final_result.strip() == "":
    #         logger.info("Final result vazio. Interrompendo o loop.")
    #         break

    #  criação da orquestração utilizando chains atualmente:

    # CRIA UMA CHAIN (cadeia) de funções ----------------------
    chain = build_chain(base_config.orchestration_steps, repo_info, context_memory, cli_params=base_config.cli_params, extractor=extractor)
    
    # EXECUTA a chain de uma vez
    final_result = chain("")
    #  --------------------------------------------------------

    output_path = os.path.join(base_config.output_info.result_path, base_config.output_info.result_file_name)
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(final_result if final_result else "")
        logger.success(f"Documentation generated successfully at {output_path}")
    except IOError as e:
        logger.error(f"Failed to write output file at {output_path}: {e}")
        raise
    
