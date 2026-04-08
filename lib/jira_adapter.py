"""Jira REST wrapper implementing TrackerAdapter.

Supports both Jira Cloud (API v3, ADF) and Jira Server/Data Center (API v2, plain text).
"""
import base64
import json as json_mod
import re
from typing import Optional

import requests

from tracker_adapter import TrackerAdapter, Ticket


def _extract_adf_text(adf: dict) -> str:
    """Recursively extract plain text from Atlassian Document Format JSON."""
    if not isinstance(adf, dict):
        return ""
    parts = []
    if adf.get("type") == "text":
        parts.append(adf.get("text", ""))
    for child in adf.get("content", []):
        parts.append(_extract_adf_text(child))
    return "".join(parts)


def _extract_adf_code_block(adf: dict, language: str) -> Optional[str]:
    """Find a codeBlock with the given language in an ADF document.

    Returns the text content of the block, or None if not found.
    """
    if not isinstance(adf, dict):
        return None
    if adf.get("type") == "codeBlock":
        attrs = adf.get("attrs", {})
        if attrs.get("language") == language:
            return _extract_adf_text(adf)
    for child in adf.get("content", []):
        result = _extract_adf_code_block(child, language)
        if result is not None:
            return result
    return None


def _markdown_to_adf(markdown: str) -> dict:
    """Convert simple markdown to minimal ADF for Jira Cloud comments."""
    paragraphs = markdown.split("\n\n")
    content = []
    for para in paragraphs:
        if not para.strip():
            continue
        content.append({
            "type": "paragraph",
            "content": [{"type": "text", "text": para.strip()}],
        })
    return {"version": 1, "type": "doc", "content": content}


class JiraAdapter(TrackerAdapter):
    def __init__(
        self,
        base_url: str,
        api_key: str,
        project: str,
        auth_type: str = "bearer",
        username: str = "",
        variant: str = "cloud",
    ):
        self.variant = variant
        self.project = project
        api_version = "3" if variant == "cloud" else "2"
        self.base = f"{base_url.rstrip('/')}/rest/api/{api_version}"

        if auth_type == "basic":
            creds = base64.b64encode(f"{username}:{api_key}".encode()).decode()
            self.headers = {
                "Authorization": f"Basic {creds}",
                "Content-Type": "application/json",
            }
        else:
            self.headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

    def get_ticket_by_key(self, ticket_key: str) -> Ticket:
        # Accept "PROJ-12" or just "12"
        if ticket_key.isdigit():
            ticket_key = f"{self.project}-{ticket_key}"

        r = requests.get(
            f"{self.base}/issue/{ticket_key}",
            headers=self.headers,
            timeout=30,
        )
        r.raise_for_status()
        return self._to_ticket(r.json())

    def _to_ticket(self, data: dict) -> Ticket:
        fields = data.get("fields", {})
        desc = fields.get("description", "") or ""

        # Cloud: description is ADF JSON; Server: plain text or wiki markup
        if isinstance(desc, dict):
            desc_text = _extract_adf_text(desc)
            # Keep the raw ADF for spec parsing — store as JSON string
            desc_raw = json_mod.dumps(desc)
        else:
            desc_text = desc
            desc_raw = desc

        labels = fields.get("labels", []) or []

        return Ticket(
            id=data["id"],
            key=data["key"],
            name=fields.get("summary", ""),
            description=desc_raw,
            label_names=labels,
        )

    def get_comments(self, issue_id: str) -> list[dict]:
        r = requests.get(
            f"{self.base}/issue/{issue_id}/comment",
            headers=self.headers,
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        items = data.get("comments", [])
        comments = []
        for item in items:
            body_raw = item.get("body", "")
            if isinstance(body_raw, dict):
                body = _extract_adf_text(body_raw)
            else:
                body = body_raw
            comments.append({
                "id": item["id"],
                "body": body,
                "created_at": item.get("created", ""),
                "actor": (
                    item.get("author", {}).get("displayName")
                    or item.get("author", {}).get("name", "unknown")
                ),
            })
        return comments

    def add_comment(self, issue_id: str, body_markdown: str) -> str:
        if self.variant == "cloud":
            payload = {"body": _markdown_to_adf(body_markdown)}
        else:
            payload = {"body": body_markdown}

        r = requests.post(
            f"{self.base}/issue/{issue_id}/comment",
            headers=self.headers,
            json=payload,
            timeout=30,
        )
        r.raise_for_status()
        return r.json()["id"]
