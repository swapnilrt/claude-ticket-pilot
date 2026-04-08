"""Shared bootstrap for skill scripts.

Adds lib/ to sys.path and provides helpers for env vars and paths.
"""
import os
import sys
from pathlib import Path

# Add lib/ to path so scripts can import ticket_spec, plane_adapter, etc.
SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_ROOT / "lib"))


def _load_dotenv():
    """Load .env file from skill root if it exists."""
    env_file = SKILL_ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if key and value and key not in os.environ:
            os.environ[key] = value


_load_dotenv()


def _env(name: str, fallback_name: str = "", default: str = "") -> str:
    """Read an env var with optional fallback to an old name."""
    val = os.environ.get(name)
    if not val and fallback_name:
        val = os.environ.get(fallback_name)
    return val or default


def _require_env(name: str, fallback_name: str = "") -> str:
    """Read a required env var with optional fallback."""
    val = _env(name, fallback_name)
    if not val:
        hint = f" (or {fallback_name})" if fallback_name else ""
        print(f"ERROR: required env var {name}{hint} is not set", file=sys.stderr)
        sys.exit(2)
    return val


def _infer_tracker_type() -> str:
    """Auto-detect tracker type from env vars present."""
    if os.environ.get("PLANE_API_KEY"):
        return "plane"
    return "plane"  # default


def state_dir() -> Path:
    return Path(os.environ.get("JIRA_SKILL_STATE", str(SKILL_ROOT / "state")))


def repos_cache_dir() -> Path:
    return Path(os.environ.get("JIRA_SKILL_REPOS", str(SKILL_ROOT / "repos-cache")))


def worktrees_dir() -> Path:
    return Path(os.environ.get("JIRA_SKILL_WORKTREES", str(SKILL_ROOT / "worktrees")))


def get_tracker():
    """Factory: return the configured TrackerAdapter."""
    tracker_type = _env("TRACKER_TYPE", default=_infer_tracker_type())

    if tracker_type == "plane":
        from plane_adapter import PlaneAdapter
        return PlaneAdapter(
            base_url=_env("TRACKER_BASE_URL", "PLANE_BASE_URL", "http://localhost:8080"),
            api_key=_require_env("TRACKER_API_KEY", "PLANE_API_KEY"),
            workspace_slug=_env("TRACKER_WORKSPACE", "PLANE_WORKSPACE_SLUG"),
            project_id=_require_env("TRACKER_PROJECT", "PLANE_PROJECT_ID"),
        )
    elif tracker_type in ("jira-cloud", "jira-server"):
        from jira_adapter import JiraAdapter
        variant = "cloud" if tracker_type == "jira-cloud" else "server"
        return JiraAdapter(
            base_url=_require_env("TRACKER_BASE_URL"),
            api_key=_require_env("TRACKER_API_KEY"),
            project=_require_env("TRACKER_PROJECT"),
            auth_type=_env("TRACKER_AUTH_TYPE", default="bearer"),
            username=_env("TRACKER_USERNAME", default=""),
            variant=variant,
        )
    else:
        print(f"ERROR: unknown TRACKER_TYPE: {tracker_type}", file=sys.stderr)
        sys.exit(2)


# Backward compat alias
get_plane = get_tracker


def get_store():
    from ticket_state import StateStore
    return StateStore(state_dir())


def get_git():
    from git_workspace import GitWorkspace
    return GitWorkspace(
        repos_cache=repos_cache_dir(),
        worktrees_root=worktrees_dir(),
    )
