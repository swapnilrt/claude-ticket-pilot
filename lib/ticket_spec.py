"""Parse the ```claude config block from a ticket description."""
import re
from dataclasses import dataclass
from typing import Optional

import yaml


@dataclass
class TicketSpec:
    repo: str
    base_branch: str = "main"
    branch_prefix: str = "claude/"
    working_dir: Optional[str] = None
    claude_command: str = "/brainstorm"
    permission_mode: str = "acceptEdits"
    skip_brainstorm: bool = False
    raw_description: str = ""

    def repo_slug(self) -> str:
        """Derive a stable folder name from the repo URL.

        git@github.com:yourorg/yourrepo.git -> yourorg-yourrepo
        https://github.com/yourorg/yourrepo -> yourorg-yourrepo
        """
        m = re.search(r"[:/]([^/:]+)/([^/]+?)(?:\.git)?/?$", self.repo)
        if not m:
            return "unknown-repo"
        return f"{m.group(1)}-{m.group(2)}"


CLAUDE_BLOCK_RE = re.compile(r"```claude\s*\n(.*?)\n```", re.DOTALL | re.IGNORECASE)
# Plane renders fenced blocks as <code class="language-claude">...</code>
HTML_CLAUDE_BLOCK_RE = re.compile(
    r'<code[^>]*class="language-claude"[^>]*>(.*?)</code>', re.DOTALL | re.IGNORECASE
)
# Jira Server wiki markup: {code:claude}...{code}
WIKI_CLAUDE_BLOCK_RE = re.compile(
    r'\{code:claude\}(.*?)\{code\}', re.DOTALL | re.IGNORECASE
)


class TicketSpecError(Exception):
    pass


def _extract_adf_claude_block(description: str) -> Optional[str]:
    """Try to parse description as ADF JSON and find a claude code block."""
    try:
        import json
        adf = json.loads(description)
        if not isinstance(adf, dict):
            return None
        return _walk_adf_for_claude(adf)
    except (json.JSONDecodeError, TypeError):
        return None


def _walk_adf_for_claude(node: dict) -> Optional[str]:
    """Walk ADF tree to find codeBlock with language=claude."""
    if not isinstance(node, dict):
        return None
    if node.get("type") == "codeBlock":
        attrs = node.get("attrs", {})
        if attrs.get("language") == "claude":
            parts = []
            for child in node.get("content", []):
                if child.get("type") == "text":
                    parts.append(child.get("text", ""))
            return "\n".join(parts)
    for child in node.get("content", []):
        result = _walk_adf_for_claude(child)
        if result is not None:
            return result
    return None


def parse_ticket(description: str) -> TicketSpec:
    """Extract the claude config block from a ticket description.

    Plane stores descriptions as HTML, so we strip tags first to recover
    the fenced code block. The block looks like:

        ```claude
        repo: git@github.com:you/repo.git
        base_branch: main
        ```
    """
    if not description:
        raise TicketSpecError("Ticket has no description")

    # Strip HTML tags so the fenced block parses regardless of editor output.
    text = re.sub(r"<br\s*/?>", "\n", description)
    text = re.sub(r"</p>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    # Decode the few HTML entities Plane commonly emits.
    text = (
        text.replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&amp;", "&")
            .replace("&quot;", '"')
            .replace("&#39;", "'")
            .replace("&nbsp;", " ")
    )

    # Priority order: ADF (Jira Cloud) → HTML (Plane) → Wiki (Jira Server) → Markdown
    raw_config = None

    # 1. ADF JSON (Jira Cloud)
    adf_result = _extract_adf_claude_block(description)
    if adf_result is not None:
        raw_config = adf_result

    # 2. HTML <code class="language-claude"> (Plane)
    if raw_config is None:
        html_match = HTML_CLAUDE_BLOCK_RE.search(description)
        if html_match:
            raw_config = html_match.group(1)
            raw_config = (
                raw_config.replace("&lt;", "<")
                    .replace("&gt;", ">")
                    .replace("&amp;", "&")
                    .replace("&quot;", '"')
                    .replace("&#39;", "'")
                    .replace("&nbsp;", " ")
            )

    # 3. Wiki markup {code:claude} (Jira Server)
    if raw_config is None:
        wiki_match = WIKI_CLAUDE_BLOCK_RE.search(text)
        if wiki_match:
            raw_config = wiki_match.group(1)

    # 4. Markdown fenced block (fallback)
    if raw_config is None:
        md_match = CLAUDE_BLOCK_RE.search(text)
        if md_match:
            raw_config = md_match.group(1)

    if raw_config is None:
        raise TicketSpecError(
            "No ```claude config block found in description. "
            "Add one with at minimum: repo: <git-url>"
        )

    try:
        config = yaml.safe_load(raw_config) or {}
    except yaml.YAMLError as e:
        raise TicketSpecError(f"Invalid YAML in claude block: {e}")

    if not isinstance(config, dict):
        raise TicketSpecError("Claude block must be a YAML mapping")
    if "repo" not in config:
        raise TicketSpecError("Claude block missing required field: repo")

    raw_description = CLAUDE_BLOCK_RE.sub("", text).strip()

    return TicketSpec(
        repo=config["repo"],
        base_branch=config.get("base_branch", "main"),
        branch_prefix=config.get("branch_prefix", "claude/"),
        working_dir=config.get("working_dir"),
        claude_command=config.get("claude_command", "/brainstorm"),
        permission_mode=config.get("permission_mode", "acceptEdits"),
        skip_brainstorm=config.get("skip_brainstorm", False),
        raw_description=raw_description,
    )
