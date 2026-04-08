#!/usr/bin/env python3
"""Post a comment back to the Plane ticket.

Usage:
    python post_comment.py <ticket-key> "comment body"
    python post_comment.py <ticket-key> --from-file /tmp/comment.md
"""
import argparse
import sys
from pathlib import Path

from _common import get_tracker, get_store


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("ticket_key")
    parser.add_argument("body", nargs="?", default=None)
    parser.add_argument("--from-file", default=None)
    args = parser.parse_args()

    if args.from_file:
        body = Path(args.from_file).read_text()
    elif args.body:
        body = args.body
    else:
        print("ERROR: provide either body argument or --from-file", file=sys.stderr)
        sys.exit(2)

    store = get_store()
    state = store.load(args.ticket_key)
    if state is None:
        print(f"ERROR: no state for {args.ticket_key}", file=sys.stderr)
        sys.exit(1)

    tracker = get_tracker()
    cid = tracker.add_comment(state.ticket_id, body)
    print(f"OK: posted comment {cid} to {args.ticket_key}")


if __name__ == "__main__":
    main()
