#!/usr/bin/env python3
"""Set up multiple tickets for parallel work in separate terminals.

Usage: python dispatch_parallel.py PROJ-12 PROJ-13 PROJ-14

For each ticket:
  1. Calls start_ticket.py to fetch + parse + create the worktree + init state
  2. Prints a ready-to-paste command for the user to launch a Claude Code
     session in that worktree

Each printed command opens an isolated Claude session that, when invoked,
uses the ticket-pilot skill to resume work on its assigned ticket.

If a ticket is already in state, it's reported as already-started and the
launch command for it is still printed (so you can resume it).
"""
import os
import subprocess
import sys
from pathlib import Path

from _common import get_store


def main():
    if len(sys.argv) < 2:
        print("Usage: dispatch_parallel.py <ticket-key> [<ticket-key> ...]", file=sys.stderr)
        sys.exit(2)

    keys = sys.argv[1:]
    scripts_dir = Path(__file__).resolve().parent
    store = get_store()

    started: list[tuple[str, str]] = []  # (ticket_key, worktree_path)
    failures: list[tuple[str, str]] = []

    for key in keys:
        print(f"\n--- Setting up {key} ---")
        # Always call start_ticket.py — it's idempotent and will tell us
        # if the ticket is already in state. This also handles key
        # normalization (12 -> ISSUE-12).
        result = subprocess.run(
            [sys.executable, str(scripts_dir / "start_ticket.py"), key],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print(f"  FAILED: {result.stderr.strip()}")
            failures.append((key, result.stderr.strip()))
            continue

        out = result.stdout
        # Two possible outputs:
        # (a) "TICKET STARTED: <key>" + "Worktree: <path>" (fresh start)
        # (b) "NOTE: ticket <key> is already in state: <phase>" (already started)
        ticket_key = ""
        worktree_path = ""
        already_started = False

        for line in out.splitlines():
            if line.startswith("Worktree:"):
                worktree_path = line.split(":", 1)[1].strip()
            elif line.startswith("TICKET STARTED:"):
                ticket_key = line.split(":", 1)[1].strip()
            elif line.startswith("NOTE: ticket"):
                # "NOTE: ticket ISSUE-12 is already in state: done"
                parts = line.split()
                if len(parts) >= 3:
                    ticket_key = parts[2]
                    already_started = True

        if already_started and ticket_key:
            state = store.load(ticket_key)
            if state:
                print(f"  Already in state ({state.phase.value}). Will resume.")
                started.append((state.ticket_key, state.worktree_path))
                continue

        if not ticket_key:
            print(f"  WARNING: couldn't parse ticket key from start_ticket.py output")
            failures.append((key, "could not determine ticket key"))
            continue

        if not worktree_path:
            state = store.load(ticket_key)
            if state:
                worktree_path = state.worktree_path

        print(f"  OK: worktree at {worktree_path}")
        started.append((ticket_key, worktree_path))

    # Print the launch commands
    print("\n" + "=" * 70)
    print("PARALLEL DISPATCH READY")
    print("=" * 70)
    if not started:
        print("No tickets ready to launch.")
        if failures:
            for key, err in failures:
                print(f"  {key}: {err}")
        sys.exit(1)

    print(f"\n{len(started)} ticket(s) ready. Open {len(started)} new terminal(s) and run:\n")
    for i, (key, worktree) in enumerate(started, 1):
        print(f"# Terminal {i} — {key}")
        print(f"cd {worktree}")
        print(f'claude "Use the ticket-pilot skill to resume work on {key}"')
        print()

    print("=" * 70)
    print("HUMAN-IN-THE-LOOP NOTES")
    print("=" * 70)
    print(
        "Each terminal will run independently with its own Claude session.\n"
        "Brainstorm questions and approval will happen in whichever terminal\n"
        "is currently asking. Switch between terminals as needed — state is\n"
        "persisted so you can pause and resume any terminal at any time.\n"
    )
    print("To check status across all tickets at once, run:")
    print("  python list_tickets.py")

    if failures:
        print("\nFailed to set up:")
        for key, err in failures:
            print(f"  {key}: {err}")


if __name__ == "__main__":
    main()
