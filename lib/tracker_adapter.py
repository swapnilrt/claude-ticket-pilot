"""Abstract tracker interface.

All issue-tracker backends (Plane, Jira, etc.) implement this ABC.
Scripts interact only with TrackerAdapter, never with a concrete class directly.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Ticket:
    id: str
    key: str
    name: str
    description: str
    label_names: list[str]


class TrackerAdapter(ABC):
    @abstractmethod
    def get_ticket_by_key(self, key: str) -> Ticket:
        """Fetch a ticket by its human-readable key (e.g. PROJ-12 or just 12)."""
        ...

    @abstractmethod
    def get_comments(self, issue_id: str) -> list[dict]:
        """Fetch all comments for an issue.

        Returns list of dicts: [{id, body, created_at, actor}]
        """
        ...

    @abstractmethod
    def add_comment(self, issue_id: str, body_markdown: str) -> str:
        """Post a markdown comment. Returns the comment ID."""
        ...

    @abstractmethod
    def create_ticket(self, title: str, description: str) -> Ticket:
        """Create a new ticket. Returns the created Ticket."""
        ...

    @abstractmethod
    def get_transitions(self, issue_id: str) -> list[dict]:
        """Get available status transitions for a ticket.

        Returns list of dicts: [{id, name}]
        """
        ...

    @abstractmethod
    def transition_ticket(self, issue_id: str, transition_name: str) -> str:
        """Move a ticket to a new status. Returns the new status name."""
        ...
