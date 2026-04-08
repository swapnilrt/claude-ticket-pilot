#!/usr/bin/env python3
"""Write tracker environment variables to the user's shell profile."""
import argparse
import os
import sys
from pathlib import Path

MARKER_START = "# >>> claude-ticket-pilot >>>"
MARKER_END = "# <<< claude-ticket-pilot <<<"


def detect_shell_profile():
    shell = os.environ.get("SHELL", "/bin/zsh")
    home = Path.home()
    if "zsh" in shell:
        return home / ".zshrc"
    return home / ".bashrc"


def build_env_block(args):
    lines = [MARKER_START]
    lines.append(f"export TRACKER_TYPE={args.tracker_type}")
    lines.append(f"export TRACKER_BASE_URL={args.base_url}")
    lines.append(f"export TRACKER_API_KEY={args.api_key}")
    lines.append(f"export TRACKER_PROJECT={args.project}")
    if args.workspace:
        lines.append(f"export TRACKER_WORKSPACE={args.workspace}")
    if args.auth_type and args.auth_type != "bearer":
        lines.append(f"export TRACKER_AUTH_TYPE={args.auth_type}")
    if args.username:
        lines.append(f"export TRACKER_USERNAME={args.username}")
    lines.append(MARKER_END)
    return "\n".join(lines)


def write_to_profile(profile_path, block):
    content = ""
    if profile_path.exists():
        content = profile_path.read_text()

    # Replace existing block if present
    if MARKER_START in content:
        start = content.index(MARKER_START)
        end = content.index(MARKER_END) + len(MARKER_END)
        content = content[:start] + block + content[end:]
    else:
        content = content.rstrip() + "\n\n" + block + "\n"

    profile_path.write_text(content)
    return profile_path


def main():
    parser = argparse.ArgumentParser(description="Configure ticket-pilot environment")
    parser.add_argument("--tracker-type", required=True, choices=["plane", "jira-cloud", "jira-server"])
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--workspace", default="")
    parser.add_argument("--auth-type", default="bearer", choices=["bearer", "basic"])
    parser.add_argument("--username", default="")
    args = parser.parse_args()

    block = build_env_block(args)
    profile = detect_shell_profile()
    write_to_profile(profile, block)

    print(f"Configuration saved to {profile}")
    print()
    print("To activate now, run:")
    print(f"  source {profile}")


if __name__ == "__main__":
    main()
