#!/usr/bin/env python3
"""Create a new ticket on the configured tracker.

Usage:
    python create_ticket.py --title "Title" --description "Full markdown description"
"""
import argparse
import sys

from _common import get_tracker


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--title", required=True)
    parser.add_argument("--description", required=True)
    args = parser.parse_args()

    tracker = get_tracker()
    ticket = tracker.create_ticket(args.title, args.description)
    print(f"OK: created {ticket.key} — {ticket.name}")
    print(f"ID: {ticket.id}")


if __name__ == "__main__":
    main()
