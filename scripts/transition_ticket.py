#!/usr/bin/env python3
"""Move a ticket to a new status/state.

Usage:
    python transition_ticket.py <ticket-key> --to "In Progress"
    python transition_ticket.py <ticket-key> --list
"""
import argparse
import sys

from _common import get_tracker, get_store


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("ticket_key")
    parser.add_argument("--to", default=None, help="Target status/transition name")
    parser.add_argument("--list", action="store_true", help="List available transitions")
    args = parser.parse_args()

    store = get_store()
    state = store.load(args.ticket_key)
    if state is None:
        print(f"ERROR: no state for {args.ticket_key}", file=sys.stderr)
        sys.exit(1)

    tracker = get_tracker()

    if args.list:
        transitions = tracker.get_transitions(state.ticket_id)
        print(f"Available transitions for {args.ticket_key}:")
        for t in transitions:
            print(f"  - {t['name']}")
        sys.exit(0)

    if not args.to:
        print("ERROR: provide --to <status> or --list", file=sys.stderr)
        sys.exit(2)

    try:
        new_status = tracker.transition_ticket(state.ticket_id, args.to)
        print(f"OK: {args.ticket_key} -> {new_status}")
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
