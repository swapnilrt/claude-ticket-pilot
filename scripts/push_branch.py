#!/usr/bin/env python3
"""Commit and push the worktree branch.

Usage: python push_branch.py <ticket-key>
"""
import sys

from _common import get_git, get_store


def main():
    if len(sys.argv) != 2:
        print("Usage: push_branch.py <ticket-key>", file=sys.stderr)
        sys.exit(2)

    key = sys.argv[1]
    store = get_store()
    git = get_git()

    state = store.load(key)
    if state is None:
        print(f"ERROR: no state for {key}", file=sys.stderr)
        sys.exit(1)

    from pathlib import Path
    worktree = Path(state.worktree_path)
    if not worktree.exists():
        print(f"ERROR: worktree {worktree} does not exist", file=sys.stderr)
        sys.exit(1)

    from ticket_state import Phase
    state.phase = Phase.PUSHING
    state.log("pushing")
    store.save(state)

    try:
        git.commit_and_push(
            worktree, state.branch, f"{state.ticket_name} [{state.ticket_key}]"
        )
    except Exception as e:
        state.phase = Phase.FAILED
        state.error = f"push failed: {e}"
        state.log("push_failed", str(e))
        store.save(state)
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    state.phase = Phase.DONE
    state.log("pushed", f"branch={state.branch}")
    store.save(state)
    print(f"OK: pushed {state.branch} to {state.repo}")


if __name__ == "__main__":
    main()
