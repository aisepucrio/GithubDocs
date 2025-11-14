from .llm_agent import *
from .load_configuration import *
from .repo_info_extraction import *
from jinja2 import Environment, FileSystemLoader

def render_prompt(template_path: str, prompt_file: str, variables: dict) -> str:
    env = Environment(loader=FileSystemLoader(template_path))
    template = env.get_template(prompt_file)
    return template.render(variables)

def populate_template(template_path: str, prompt_file: str) -> str:

    return 