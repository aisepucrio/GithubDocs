from typing import Dict, List, Optional
from pydantic import BaseModel


class IssueInfo(BaseModel):
    """DTO (Data Transfer Object) for GitHub issue information."""
    number: int
    title: str
    state: str
    body: Optional[str]
    author: str
    created_at: str
    closed_at: Optional[str]
    labels: List[str]
    pull_requests: List[int]
    closing_commit: Optional[str]

    def to_dict(self) -> Dict:
        """Converts the DTO to a dictionary."""
        return {
            "number": self.number,
            "title": self.title,
            "state": self.state,
            "body": self.body,
            "author": self.author,
            "created_at": self.created_at,
            "closed_at": self.closed_at,
            "labels": self.labels,
            "pull_requests": self.pull_requests,
            "closing_commit": self.closing_commit
        }
