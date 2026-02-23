from typing import Optional, List, Dict
from langchain_core.tools import tool
from src.github_integration import IssueTracker
from src.log import CustomLogger

logger = CustomLogger()


class GitHubToolsManager:
    """Manager class for GitHub issue tools that encapsulates state and provides tools for LLM agents."""
    
    def __init__(self, issue_tracker: Optional[IssueTracker] = None, commit_messages: List[str] = None):
        """
        Initialize the GitHub tools manager.
        
        Args:
            issue_tracker: Optional IssueTracker instance for GitHub API access
            commit_messages: Optional list of commit messages to analyze
        """
        self.issue_tracker = issue_tracker
        self.commit_messages = commit_messages or []
    
    def search_issues_in_commits(self) -> str:
        """Search for GitHub issues mentioned in commit messages."""
        if not self.issue_tracker:
            return "GitHub issues functionality is not configured. No token was provided."
        
        if not self.commit_messages:
            return "No commit messages available for analysis."
        
        try:
            # Analyze all provided commits searching for issues
            all_issues = {}
            for message in self.commit_messages:
                issues = self.issue_tracker.find_issues_in_text(message)
                for num, info in issues.items():
                    if num not in all_issues:
                        all_issues[num] = info.to_dict()
            
            if not all_issues:
                return "No GitHub issues were mentioned in the analyzed commits."
            
            result = f"Found {len(all_issues)} issue(s) mentioned in commits:\n\n"
            
            for num, issue in sorted(all_issues.items()):
                result += f"Issue #{num}: {issue['title']}\n"
                result += f"  Status: {issue['state']}\n"
                result += f"  Author: {issue['author']}\n"
                
                if issue.get('labels'):
                    result += f"  Labels: {', '.join(issue['labels'])}\n"
                
                if issue.get('body'):
                    # Limit description size (context concerns)
                    body = issue['body'][:300]
                    if len(issue['body']) > 300:
                        body += "..."
                    result += f"  Description: {body}\n"
                
                result += "\n"
            
            return result.strip()
            
        except Exception as e:
            logger.warning(f"Error fetching issues: {e}")
            return f"Error fetching issue information: {str(e)}"
    
    def get_issue_details(self, issue_number: int) -> str:
        """Get detailed information about a specific GitHub issue by its number."""
        if not self.issue_tracker:
            return "GitHub issues functionality is not configured."
        
        try:
            context = self.issue_tracker.get_issue_resolution_context(issue_number)
            
            if not context:
                return f"Issue #{issue_number} was not found in the repository."
            
            return context
            
        except Exception as e:
            logger.warning(f"Error fetching issue #{issue_number}: {e}")
            return f"Error fetching issue #{issue_number}: {str(e)}"
    
    @staticmethod
    def extract_issue_numbers(text: str) -> str:
        """Extract GitHub issue numbers from a given text."""
        try:
            issue_numbers = IssueTracker.extract_issue_numbers(text)
            
            if not issue_numbers:
                return "No issue references were found in the provided text."
            
            return f"Issues found in text: {', '.join(f'#{num}' for num in issue_numbers)}"
            
        except Exception as e:
            return f"Error extracting issue numbers: {str(e)}"
    
    def get_tools(self) -> List:
        """
        Get langchain tools configured with this manager instance.
        
        Returns:
            List of langchain tool functions
        """
        # Create closures that capture self for instance methods
        @tool
        def search_github_issues_in_commits() -> str:
            """Search for GitHub issues mentioned in commit messages. Returns information about referenced issues including title, status, author, labels, and description."""
            return self.search_issues_in_commits()
        
        @tool
        def get_github_issue_details(issue_number: int) -> str:
            """Get detailed information about a specific GitHub issue by its number. Returns the full context needed to understand and resolve the issue."""
            return self.get_issue_details(issue_number)
        
        @tool
        def extract_issue_numbers_from_text(text: str) -> str:
            """Extract GitHub issue numbers from a given text. Identifies patterns like #123, #456, etc. and returns the list of found issue numbers."""
            return GitHubToolsManager.extract_issue_numbers(text)
        
        return [
            search_github_issues_in_commits,
            get_github_issue_details,
            extract_issue_numbers_from_text,
        ]


# Global instance for backward compatibility
_tools_manager: Optional[GitHubToolsManager] = None


def set_issue_tracker(tracker: Optional[IssueTracker], commit_messages: List[str] = None):
    """
    Legacy function for backward compatibility. Creates a global GitHubToolsManager instance.
    
    Args:
        tracker: IssueTracker instance
        commit_messages: List of commit messages
    """
    global _tools_manager
    _tools_manager = GitHubToolsManager(tracker, commit_messages)


def get_github_issue_tools() -> List:
    """
    Get GitHub issue tools from the global manager instance.
    
    Returns:
        List of langchain tools, or empty list if not configured
    """
    if _tools_manager:
        return _tools_manager.get_tools()
    return []
