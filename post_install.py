#!/usr/bin/env python3
"""Post-install script for claude-ticket-pilot.

Run automatically after `claude plugins install github:yourorg/claude-ticket-pilot`.
Handles: pip deps, superpowers dependency, .env scaffolding, skill registration.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent
PLUGINS_DIR = Path.home() / ".claude" / "plugins"
SETTINGS_FILE = Path.home() / ".claude" / "settings.json"


def install_pip_deps():
    print("[1/4] Installing Python dependencies...")
    req_file = SKILL_ROOT / "requirements.txt"
    if req_file.exists():
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(req_file), "-q"],
            check=True,
        )
    print("      Done.")


def install_superpowers():
    print("[2/4] Checking superpowers dependency...")
    sp_dir = PLUGINS_DIR / "superpowers"
    if sp_dir.exists():
        print("      superpowers already installed.")
        return
    cache_dir = PLUGINS_DIR / "cache" / "claude-plugins-official" / "superpowers"
    if cache_dir.exists():
        print("      superpowers found in cache.")
        return
    print("      Installing superpowers from GitHub...")
    try:
        subprocess.run(
            ["git", "clone", "https://github.com/anthropics/claude-plugins-official.git",
             str(PLUGINS_DIR / "cache" / "claude-plugins-official")],
            check=True, capture_output=True,
        )
        print("      Done.")
    except subprocess.CalledProcessError:
        print("      WARNING: Could not install superpowers automatically.")
        print("      Install it manually if you want brainstorming support.")


def scaffold_env():
    print("[3/4] Setting up configuration...")
    env_file = SKILL_ROOT / ".env"
    if env_file.exists():
        print("      .env already exists, skipping.")
        return

    example = SKILL_ROOT / ".env.example"
    if not example.exists():
        print("      No .env.example found, skipping.")
        return

    print()
    print("      Configure your tracker connection:")
    print()

    tracker_type = input("      Tracker type (plane/jira-cloud/jira-server) [plane]: ").strip() or "plane"
    base_url = input("      Base URL: ").strip()
    api_key = input("      API key: ").strip()
    project = input("      Project ID/key: ").strip()

    workspace = ""
    auth_type = "bearer"
    username = ""

    if tracker_type == "plane":
        workspace = input("      Workspace slug: ").strip()
    elif tracker_type in ("jira-cloud", "jira-server"):
        auth_type = input("      Auth type (bearer/basic) [bearer]: ").strip() or "bearer"
        if auth_type == "basic":
            username = input("      Username/email: ").strip()

    content = f"""# Tracker config
TRACKER_TYPE={tracker_type}
TRACKER_BASE_URL={base_url}
TRACKER_API_KEY={api_key}
TRACKER_PROJECT={project}
TRACKER_WORKSPACE={workspace}
TRACKER_AUTH_TYPE={auth_type}
TRACKER_USERNAME={username}

# Polling config
PLANE_POLL_INTERVAL=120
PLANE_POLL_TIMEOUT=3600
"""
    env_file.write_text(content)
    print(f"      Saved to {env_file}")


def register_skill():
    print("[4/4] Registering skill with Claude Code...")
    print(f"      Skill installed at: {SKILL_ROOT}")
    print("      Claude Code will auto-discover it on next launch.")


def main():
    print()
    print("=" * 50)
    print("  claude-ticket-pilot installer")
    print("=" * 50)
    print()

    install_pip_deps()
    install_superpowers()
    scaffold_env()
    register_skill()

    print()
    print("=" * 50)
    print("  Installation complete!")
    print("=" * 50)
    print()
    print("  Start Claude Code and say: work on PROJ-12")
    print()


if __name__ == "__main__":
    main()
