"""Per-ticket state, persisted to JSON.

This is the source of truth for resume. The state file plus the worktree
on disk together fully reconstruct an in-flight ticket so a fresh Claude
session can pick up exactly where the previous one left off.
"""
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional


class Phase(str, Enum):
    NEW = "new"                            # just fetched, nothing done yet
    READING_CODE = "reading_code"          # Claude is exploring the codebase
    BRAINSTORMING = "brainstorming"        # Claude has questions, hasn't asked yet
    AWAITING_ANSWERS = "awaiting_answers"  # questions asked, waiting for human
    PLANNING = "planning"                  # answers received, plan being written
    AWAITING_APPROVAL = "awaiting_approval"  # plan written, waiting for human
    BUILDING = "building"                  # implementing the plan
    PUSHING = "pushing"                    # committing & pushing
    DONE = "done"
    FAILED = "failed"


PHASE_DESCRIPTIONS = {
    Phase.NEW: "Ticket fetched, nothing started yet",
    Phase.READING_CODE: "Reading the codebase to understand context",
    Phase.BRAINSTORMING: "Formulating clarifying questions",
    Phase.AWAITING_ANSWERS: "Waiting for the user to answer brainstorm questions",
    Phase.PLANNING: "Writing the implementation plan",
    Phase.AWAITING_APPROVAL: "Plan written, waiting for user approval",
    Phase.BUILDING: "Implementing the approved plan",
    Phase.PUSHING: "Committing and pushing the branch",
    Phase.DONE: "Complete — branch pushed, ticket commented",
    Phase.FAILED: "Failed — see error field",
}


@dataclass
class TicketState:
    ticket_id: str
    ticket_key: str
    ticket_name: str
    ticket_description: str  # the parsed raw description (no spec block)
    repo: str
    branch: str
    worktree_path: str
    base_branch: str = "main"
    permission_mode: str = "acceptEdits"
    phase: Phase = Phase.NEW
    brainstorm_questions: Optional[str] = None
    user_answers: Optional[str] = None
    plan: Optional[str] = None
    build_summary: Optional[str] = None
    error: Optional[str] = None
    history: list[dict] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def log(self, event: str, detail: str = "") -> None:
        ts = datetime.now(timezone.utc).isoformat()
        self.history.append({"ts": ts, "event": event, "detail": detail})
        self.updated_at = ts


class StateStore:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, ticket_key: str) -> Path:
        # Use the human key (PROJ-12) as the filename — easier to find
        safe = ticket_key.replace("/", "-").replace("\\", "-")
        return self.root / f"{safe}.json"

    def exists(self, ticket_key: str) -> bool:
        return self._path(ticket_key).exists()

    def load(self, ticket_key: str) -> Optional[TicketState]:
        p = self._path(ticket_key)
        if not p.exists():
            return None
        data = json.loads(p.read_text())
        data["phase"] = Phase(data["phase"])
        return TicketState(**data)

    def save(self, state: TicketState) -> None:
        if not state.created_at:
            state.created_at = datetime.now(timezone.utc).isoformat()
        state.updated_at = datetime.now(timezone.utc).isoformat()
        data = asdict(state)
        data["phase"] = state.phase.value
        self._path(state.ticket_key).write_text(json.dumps(data, indent=2))

    def list_all(self) -> list[TicketState]:
        out = []
        for p in sorted(self.root.glob("*.json")):
            try:
                data = json.loads(p.read_text())
                data["phase"] = Phase(data["phase"])
                out.append(TicketState(**data))
            except Exception:
                continue
        return out

    def delete(self, ticket_key: str) -> bool:
        p = self._path(ticket_key)
        if p.exists():
            p.unlink()
            return True
        return False
