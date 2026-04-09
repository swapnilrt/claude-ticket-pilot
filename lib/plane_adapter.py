"""Plane REST wrapper implementing TrackerAdapter."""
import re
from typing import Optional

import requests

from tracker_adapter import TrackerAdapter, Ticket


def _strip_html(html: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", html or "")
    text = re.sub(r"</p>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


class PlaneAdapter(TrackerAdapter):
    def __init__(self, base_url: str, api_key: str, workspace_slug: str, project_id: str):
        self.base = (
            f"{base_url.rstrip('/')}/api/v1/workspaces/{workspace_slug}/projects/{project_id}"
        )
        self.headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
        self._label_names: Optional[dict[str, str]] = None

    def _load_labels(self) -> dict[str, str]:
        if self._label_names is not None:
            return self._label_names
        r = requests.get(f"{self.base}/labels/", headers=self.headers, timeout=30)
        r.raise_for_status()
        data = r.json()
        items = data.get("results", data) if isinstance(data, dict) else data
        self._label_names = {label["id"]: label["name"] for label in items}
        return self._label_names

    def get_ticket_by_id(self, issue_id: str) -> Ticket:
        r = requests.get(f"{self.base}/issues/{issue_id}/", headers=self.headers, timeout=30)
        r.raise_for_status()
        return self._to_ticket(r.json())

    def get_ticket_by_key(self, ticket_key: str) -> Ticket:
        m = re.search(r"(\d+)$", ticket_key)
        if not m:
            raise ValueError(f"Invalid ticket key: {ticket_key}")
        seq_id = int(m.group(1))

        r = requests.get(f"{self.base}/issues/", headers=self.headers, timeout=30)
        r.raise_for_status()
        data = r.json()
        items = data.get("results", data) if isinstance(data, dict) else data
        for item in items:
            if item.get("sequence_id") == seq_id:
                return self._to_ticket(item)
        raise ValueError(f"No ticket with sequence_id {seq_id} found in project")

    def _to_ticket(self, data: dict) -> Ticket:
        labels = self._load_labels()
        label_ids = data.get("labels", []) or []
        desc = data.get("description_html") or data.get("description_stripped") or ""
        return Ticket(
            id=data["id"],
            key=f"ISSUE-{data.get('sequence_id', '?')}",
            name=data["name"],
            description=desc,
            label_names=[labels.get(lid, lid) for lid in label_ids],
        )

    def get_comments(self, issue_id: str) -> list[dict]:
        r = requests.get(
            f"{self.base}/issues/{issue_id}/comments/",
            headers=self.headers,
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        items = data.get("results", data) if isinstance(data, dict) else data
        comments = []
        for item in items:
            body = _strip_html(item.get("comment_html", "") or item.get("comment", ""))
            comments.append({
                "id": item["id"],
                "body": body,
                "created_at": item.get("created_at", ""),
                "actor": item.get("actor_detail", {}).get("display_name", "unknown"),
            })
        return comments

    def add_comment(self, issue_id: str, body_markdown: str) -> str:
        html_body = body_markdown.replace("\n\n", "</p><p>").replace("\n", "<br>")
        html = f"<p>{html_body}</p>"
        r = requests.post(
            f"{self.base}/issues/{issue_id}/comments/",
            headers=self.headers,
            json={"comment_html": html},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()["id"]

    def get_transitions(self, issue_id: str) -> list[dict]:
        # Plane uses state groups: backlog, unstarted, started, completed, cancelled
        r = requests.get(f"{self.base}/states/", headers=self.headers, timeout=30)
        r.raise_for_status()
        data = r.json()
        items = data.get("results", data) if isinstance(data, dict) else data
        return [{"id": s["id"], "name": s["name"]} for s in items]

    def transition_ticket(self, issue_id: str, transition_name: str) -> str:
        states = self.get_transitions(issue_id)
        match = None
        for s in states:
            if s["name"].lower() == transition_name.lower():
                match = s
                break
        if not match:
            available = ", ".join(s["name"] for s in states)
            raise ValueError(
                f"State '{transition_name}' not available. Available: {available}"
            )
        r = requests.patch(
            f"{self.base}/issues/{issue_id}/",
            headers=self.headers,
            json={"state": match["id"]},
            timeout=30,
        )
        r.raise_for_status()
        return match["name"]

    def create_ticket(self, title: str, description: str) -> Ticket:
        html_body = description.replace("\n\n", "</p><p>").replace("\n", "<br>")
        html = f"<p>{html_body}</p>"
        r = requests.post(
            f"{self.base}/issues/",
            headers=self.headers,
            json={"name": title, "description_html": html},
            timeout=30,
        )
        r.raise_for_status()
        return self._to_ticket(r.json())
