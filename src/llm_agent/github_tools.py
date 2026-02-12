from typing import Optional, List, Dict
from langchain_core.tools import tool
from src.github_integration import IssueTracker
from src.log import CustomLogger

logger = CustomLogger()

# Variável global para armazenar o tracker (será injetada pelo facade)
_issue_tracker: Optional[IssueTracker] = None
_commit_messages: List[str] = []


def set_issue_tracker(tracker: Optional[IssueTracker], commit_messages: List[str] = None):
    global _issue_tracker, _commit_messages
    _issue_tracker = tracker
    _commit_messages = commit_messages or []


@tool
def search_github_issues_in_commits() -> str:
    if not _issue_tracker:
        return "Funcionalidade de issues do GitHub não está configurada. Nenhum token foi fornecido."
    
    if not _commit_messages:
        return "Nenhuma mensagem de commit disponível para análise."
    
    try:
        # analiza todos os commits fornecidos em busca de issues
        all_issues = {}
        for message in _commit_messages:
            issues = _issue_tracker.find_issues_in_text(message)
            for num, info in issues.items():
                if num not in all_issues:
                    all_issues[num] = info.to_dict()
        
        if not all_issues:
            return "Nenhuma issue do GitHub foi mencionada nos commits analisados."
        
        result = f"Encontradas {len(all_issues)} issue(s) mencionadas nos commits:\n\n"
        
        for num, issue in sorted(all_issues.items()):
            result += f"Issue #{num}: {issue['title']}\n"
            result += f"  Status: {issue['state']}\n"
            result += f"  Autor: {issue['author']}\n"
            
            if issue.get('labels'):
                result += f"  Labels: {', '.join(issue['labels'])}\n"
            
            if issue.get('body'):
                # limita o tamanho da descrição (contexto worries)
                body = issue['body'][:300]
                if len(issue['body']) > 300:
                    body += "..."
                result += f"  Descrição: {body}\n"
            
            result += "\n"
        
        return result.strip()
        
    except Exception as e:
        logger.warning(f"Erro ao buscar issues: {e}")
        return f"Erro ao buscar informações de issues: {str(e)}"


@tool
def get_github_issue_details(issue_number: int) -> str:
    if not _issue_tracker:
        return "Funcionalidade de issues do GitHub não está configurada."
    
    try:
        context = _issue_tracker.get_issue_resolution_context(issue_number)
        
        if not context:
            return f"Issue #{issue_number} não foi encontrada no repositório."
        
        return context
        
    except Exception as e:
        logger.warning(f"Erro ao buscar issue #{issue_number}: {e}")
        return f"Erro ao buscar issue #{issue_number}: {str(e)}"


@tool
def extract_issue_numbers_from_text(text: str) -> str:
    try:
        issue_numbers = IssueTracker.extract_issue_numbers(text)
        
        if not issue_numbers:
            return "Nenhuma referência a issue foi encontrada no texto fornecido."
        
        return f"Issues encontradas no texto: {', '.join(f'#{num}' for num in issue_numbers)}"
        
    except Exception as e:
        return f"Erro ao extrair números de issues: {str(e)}"


def get_github_issue_tools() -> List:
    return [
        search_github_issues_in_commits,
        get_github_issue_details,
        extract_issue_numbers_from_text,
    ]
