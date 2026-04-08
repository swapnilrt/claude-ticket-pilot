#!/usr/bin/env python3
"""Start work on a ticket. Idempotent — safe to call on an existing ticket.

Usage: python start_ticket.py <ticket-key-or-id>

If state already exists for this ticket, prints a hint to use resume_ticket
instead. Otherwise: fetches the ticket, parses the spec, sets up the
worktree, writes initial state, and prints the ticket context for Claude.
"""
import sys
from datetime import datetime, timezone

from _common import get_git, get_tracker, get_store


def main():
    if len(sys.argv) != 2:
        print("Usage: start_ticket.py <ticket-key-or-id>", file=sys.stderr)
        sys.exit(2)

    ticket_arg = sys.argv[1]
    tracker = get_tracker()
    store = get_store()
    git = get_git()

    # Fetch the ticket — try as UUID first, then as PROJ-N key
    try:
        if "-" in ticket_arg and len(ticket_arg) > 20:
            ticket = tracker.get_ticket_by_id(ticket_arg)
        else:
            ticket = tracker.get_ticket_by_key(ticket_arg)
    except Exception as e:
        print(f"ERROR: could not fetch ticket {ticket_arg}: {e}", file=sys.stderr)
        sys.exit(1)

    # Check if state already exists
    if store.exists(ticket.key):
        existing = store.load(ticket.key)
        print(f"NOTE: ticket {ticket.key} is already in state: {existing.phase.value}")
        print(f"Use resume_ticket.py {ticket.key} to continue.")
        sys.exit(0)

    # Parse the spec block
    from ticket_spec import parse_ticket, TicketSpecError
    try:
        spec = parse_ticket(ticket.description)
    except TicketSpecError as e:
        print(f"ERROR: ticket {ticket.key} has no valid claude config block: {e}", file=sys.stderr)
        print()
        print("Add a block like this to the ticket description:")
        print()
        print("```claude")
        print("repo: git@github.com:you/repo.git")
        print("base_branch: main")
        print("```")
        sys.exit(1)

    # Set up the worktree
    try:
        worktree, branch = git.create(ticket.key, spec)
    except Exception as e:
        print(f"ERROR: failed to create worktree: {e}", file=sys.stderr)
        sys.exit(1)

    # Write initial state
    from ticket_state import TicketState, Phase
    state = TicketState(
        ticket_id=ticket.id,
        ticket_key=ticket.key,
        ticket_name=ticket.name,
        ticket_description=spec.raw_description,
        repo=spec.repo,
        branch=branch,
        worktree_path=str(worktree),
        base_branch=spec.base_branch,
        permission_mode=spec.permission_mode,
        phase=Phase.NEW,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    state.log("started", f"worktree at {worktree}")
    store.save(state)

    # Print structured context for Claude to read
    print("=" * 60)
    print(f"TICKET STARTED: {ticket.key}")
    print("=" * 60)
    print(f"Title:         {ticket.name}")
    print(f"Repo:          {spec.repo}")
    print(f"Base branch:   {spec.base_branch}")
    print(f"Worktree:      {worktree}")
    print(f"Branch:        {branch}")
    print(f"State file:    {store._path(ticket.key)}")
    print(f"Phase:         {state.phase.value}")
    print()
    print("--- Ticket description ---")
    print(spec.raw_description)
    print()
    print("--- Next steps for Claude ---")
    print("1. cd into the worktree")
    print("2. Read enough of the codebase to understand the change")
    print("3. Ask the user clarifying questions")
    print("4. After answers, save progress with:")
    print(f"   python save_progress.py {ticket.key} --phase awaiting_approval \\")
    print(f"     --questions '...' --answers '...' --plan '...'")


if __name__ == "__main__":
    main()
