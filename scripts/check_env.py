#!/usr/bin/env python3
"""Check whether required environment variables are set for ticket-pilot."""
import os
import sys

REQUIRED = ["TRACKER_TYPE", "TRACKER_BASE_URL", "TRACKER_API_KEY", "TRACKER_PROJECT"]

CONDITIONAL = {
    "plane": {"required": ["TRACKER_WORKSPACE"], "optional": []},
    "jira-cloud": {"required": [], "optional": ["TRACKER_AUTH_TYPE", "TRACKER_USERNAME"]},
    "jira-server": {"required": [], "optional": ["TRACKER_AUTH_TYPE", "TRACKER_USERNAME"]},
}


def main():
    missing = [v for v in REQUIRED if not os.environ.get(v)]
    tracker_type = os.environ.get("TRACKER_TYPE", "")

    conditional_missing = []
    if tracker_type in CONDITIONAL:
        for v in CONDITIONAL[tracker_type]["required"]:
            if not os.environ.get(v):
                conditional_missing.append(v)

    if not missing and not conditional_missing:
        print("OK: All required environment variables are set.")
        print(f"  TRACKER_TYPE={tracker_type}")
        print(f"  TRACKER_BASE_URL={os.environ.get('TRACKER_BASE_URL', '')}")
        print(f"  TRACKER_PROJECT={os.environ.get('TRACKER_PROJECT', '')}")
        sys.exit(0)

    print("MISSING: The following required environment variables are not set:")
    for v in missing:
        print(f"  - {v}")
    for v in conditional_missing:
        print(f"  - {v} (required for {tracker_type})")
    print()
    print("Run setup to configure them, or export them in your shell profile.")
    sys.exit(1)


if __name__ == "__main__":
    main()
