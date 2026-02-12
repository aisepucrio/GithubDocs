import re
from typing import Dict, List, Optional
from github import Github, GithubException
from src.log import CustomLogger
from .issue_dto import IssueInfo

logger = CustomLogger()


class IssueTracker:
    # common patterns for issues
    ISSUE_PATTERNS = [
        r'#(\d+)',  # #123
        r'(?:fix|fixes|fixed|close|closes|closed|resolve|resolves|resolved)\s+#(\d+)',  # fix #123
        r'(?:issue|gh)-?(\d+)',  # issue-123, gh123
    ]

    @staticmethod
    def extract_issue_numbers(text: str) -> List[int]:
        issue_numbers = set()
        
        for pattern in IssueTracker.ISSUE_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                issue_num = int(match.group(match.lastindex))
                issue_numbers.add(issue_num)
        
        return sorted(list(issue_numbers))

    def __init__(self, repo_full_name: str, github_token: Optional[str] = None):
        self.repo_full_name = repo_full_name
        self.github_token = github_token
        
        if github_token:
            self.github = Github(github_token)
        else:
            self.github = Github()
            logger.warning("GitHub token not provided. Using API without authentication (reduced rate limit).")
        
        try:
            self.repo = self.github.get_repo(repo_full_name)
            logger.info(f"Connected to repository: {repo_full_name}")
        except GithubException as e:
            logger.error(f"Error accessing repository {repo_full_name}: {e}")
            raise

    def _get_related_pull_requests(self, issue, issue_number: int) -> List[int]:
        """Fetch Pull Requests related to the issue through the timeline."""
        pr_numbers = []
        try:
            timeline = issue.get_timeline()
            for event in timeline:
                if event.event == "cross-referenced" and hasattr(event, 'source'):
                    if hasattr(event.source, 'issue') and event.source.issue.pull_request:
                        pr_numbers.append(event.source.issue.number)
        except Exception as e:
            logger.debug(f"Could not fetch timeline for issue #{issue_number}: {e}")
        
        return pr_numbers

    def _get_closing_commit(self, issue, issue_number: int) -> Optional[str]:
        """Fetch the commit that closed the issue."""
        if issue.state != "closed":
            return None
        
        try:
            events = issue.get_events()
            for event in events:
                if event.event == "closed" and event.commit_id:
                    return event.commit_id
        except Exception as e:
            logger.debug(f"Could not fetch events for issue #{issue_number}: {e}")
        
        return None

    def get_issue(self, issue_number: int) -> Optional[IssueInfo]:
        """Main method that fetches an issue and returns the complete IssueInfo object."""
        try:
            issue = self.repo.get_issue(issue_number)
            
            pr_numbers = self._get_related_pull_requests(issue, issue_number)
            closing_commit = self._get_closing_commit(issue, issue_number)
            
            return IssueInfo(
                number=issue.number,
                title=issue.title,
                state=issue.state,
                body=issue.body,
                author=issue.user.login if issue.user else "unknown",
                created_at=issue.created_at.isoformat() if issue.created_at else "",
                closed_at=issue.closed_at.isoformat() if issue.closed_at else None,
                labels=[label.name for label in issue.labels],
                pull_requests=pr_numbers,
                closing_commit=closing_commit
            )
            
        except GithubException as e:
            if e.status == 404:
                logger.warning(f"Issue #{issue_number} not found in repository {self.repo_full_name}")
            else:
                logger.error(f"Error fetching issue #{issue_number}: {e}")
            return None

    def find_issues_in_text(self, text: str) -> Dict[int, IssueInfo]:
        issue_numbers = IssueTracker.extract_issue_numbers(text)
        issues = {}
        
        for num in issue_numbers:
            issue_info = self.get_issue(num)
            if issue_info:
                issues[num] = issue_info
        
        return issues

    def analyze_commits(self, commits_data: List[Dict]) -> Dict[str, any]:
        all_issues = {}
        commits_by_issue = {}
        
        for commit in commits_data:
            message = commit.get("message", "")
            commit_hash = commit.get("hash", "")
            
            issues = self.find_issues_in_text(message)
            
            for issue_num, issue_info in issues.items():
                if issue_num not in all_issues:
                    all_issues[issue_num] = issue_info.to_dict()
                
                if issue_num not in commits_by_issue:
                    commits_by_issue[issue_num] = []
                commits_by_issue[issue_num].append({
                    "hash": commit_hash,
                    "message": message,
                    "date": commit.get("date", "")
                })
        
        return {
            "issues": all_issues,
            "commits_by_issue": commits_by_issue,
            "total_issues_referenced": len(all_issues)
        }

    def get_issue_resolution_context(self, issue_number: int) -> Optional[str]:
        issue = self.get_issue(issue_number)
        if not issue:
            return None
        
        context = f"""
                    Issue #{issue.number}: {issue.title}
                    Status: {issue.state}
                    Author: {issue.author}
                    Created at: {issue.created_at}
                   """
        
        if issue.closed_at:
            context += f"Closed at: {issue.closed_at}\n"
        
        if issue.labels:
            context += f"Labels: {', '.join(issue.labels)}\n"
        
        if issue.closing_commit:
            context += f"Closing commit: {issue.closing_commit}\n"
        
        if issue.pull_requests:
            context += f"Related Pull Requests: {', '.join(f'#{pr}' for pr in issue.pull_requests)}\n"
        
        if issue.body:
            body_preview = issue.body[:500] + "..." if len(issue.body) > 500 else issue.body
            context += f"\nDescription:\n{body_preview}\n"
        
        return context.strip()

    def close(self):
        if hasattr(self.github, 'close'):
            self.github.close()