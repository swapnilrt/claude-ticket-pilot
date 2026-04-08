#!/usr/bin/env python3
"""List all in-flight tickets and their current phase.

Usage: python list_tickets.py [--all]

By default hides DONE tickets. Use --all to show everything.
"""
import sys

from _common import get_store


def main():
    show_all = "--all" in sys.argv
    store = get_store()
    states = store.list_all()

    if not states:
        print("No tickets in state. Use start_ticket.py to begin.")
        return

    from ticket_state import Phase

    visible = states if show_all else [s for s in states if s.phase != Phase.DONE]
    if not visible:
        print(f"No active tickets ({len(states)} done — use --all to show).")
        return

    # Print as a table
    rows = []
    for s in visible:
        rows.append((s.ticket_key, s.phase.value, s.ticket_name[:50], s.branch))

    key_w = max(len("KEY"), max(len(r[0]) for r in rows))
    phase_w = max(len("PHASE"), max(len(r[1]) for r in rows))
    name_w = max(len("TITLE"), max(len(r[2]) for r in rows))

    fmt = f"{{:<{key_w}}}  {{:<{phase_w}}}  {{:<{name_w}}}  {{}}"
    print(fmt.format("KEY", "PHASE", "TITLE", "BRANCH"))
    print(fmt.format("-" * key_w, "-" * phase_w, "-" * name_w, "------"))
    for r in rows:
        print(fmt.format(*r))

    print()
    from ticket_state import Phase as P
    done_count = sum(1 for s in states if s.phase == P.DONE)
    active_count = len(states) - done_count
    print(f"{active_count} active, {done_count} done")


if __name__ == "__main__":
    main()
