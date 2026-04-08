#!/usr/bin/env python3
"""Resume work on a ticket. Reads the state file and prints a structured
summary so a fresh Claude session can pick up exactly where the previous
one left off.

Usage: python resume_ticket.py <ticket-key>
"""
import sys

from _common import get_store, get_tracker


def main():
    if len(sys.argv) != 2:
        print("Usage: resume_ticket.py <ticket-key>", file=sys.stderr)
        sys.exit(2)

    key = sys.argv[1]
    store = get_store()
    state = store.load(key)
    if state is None:
        print(f"ERROR: no state found for {key}. Use start_ticket.py to begin.", file=sys.stderr)
        sys.exit(1)

    from ticket_state import Phase, PHASE_DESCRIPTIONS

    # If waiting for human input, do a one-shot check for new tracker comments
    if state.phase in (Phase.AWAITING_ANSWERS, Phase.AWAITING_APPROVAL):
        try:
            tracker = get_tracker()
            comments = tracker.get_comments(state.ticket_id)
            new_comments = [
                c for c in comments
                if c["created_at"] > state.updated_at
            ]
            if new_comments:
                bodies = "\n\n".join(c["body"] for c in new_comments)
                n = len(new_comments)

                if state.phase == Phase.AWAITING_ANSWERS:
                    state.user_answers = bodies
                    state.phase = Phase.PLANNING
                    state.log("auto_received_answers", f"Found {n} new comment(s) on tracker")
                    store.save(state)
                    print(f"[auto] Detected {n} new comment(s) on tracker — moved to planning phase.")

                elif state.phase == Phase.AWAITING_APPROVAL:
                    combined = bodies.lower()
                    if any(w in combined for w in ["yes", "approve", "approved", "lgtm", "go ahead", "ship it"]):
                        state.phase = Phase.BUILDING
                        state.log("auto_approved", f"Approval detected in tracker comment")
                        store.save(state)
                        print(f"[auto] Approval detected on tracker — moved to building phase.")
                    elif any(w in combined for w in ["no", "reject", "stop"]):
                        state.log("approval_rejected", f"Rejection detected in tracker comment")
                        store.save(state)
                        print(f"[auto] Rejection detected on tracker. Staying in awaiting_approval.")
                    else:
                        state.log("approval_feedback", bodies[:500])
                        store.save(state)
                        print(f"[auto] Feedback received on tracker. Staying in awaiting_approval for plan revision.")
                print()
        except Exception as e:
            print(f"[warn] Could not check tracker for comments: {e}", file=sys.stderr)

    print("=" * 60)
    print(f"RESUMING TICKET: {state.ticket_key}")
    print("=" * 60)
    print(f"Title:         {state.ticket_name}")
    print(f"Repo:          {state.repo}")
    print(f"Worktree:      {state.worktree_path}")
    print(f"Branch:        {state.branch}")
    print(f"Phase:         {state.phase.value}")
    print(f"Means:         {PHASE_DESCRIPTIONS[state.phase]}")
    print(f"Last update:   {state.updated_at}")
    print()

    print("--- Ticket description ---")
    print(state.ticket_description)
    print()

    if state.brainstorm_questions:
        print("--- Questions previously asked ---")
        print(state.brainstorm_questions)
        print()

    if state.user_answers:
        print("--- User's previous answers ---")
        print(state.user_answers)
        print()

    if state.plan:
        print("--- Plan (drafted previously) ---")
        print(state.plan)
        print()

    if state.build_summary:
        print("--- Build summary ---")
        print(state.build_summary)
        print()

    if state.error:
        print("--- ERROR from previous run ---")
        print(state.error)
        print()

    print("--- History ---")
    for entry in state.history[-10:]:
        detail = f" — {entry['detail']}" if entry.get("detail") else ""
        print(f"  [{entry['ts']}] {entry['event']}{detail}")
    print()

    # Tell Claude exactly what to do next based on the phase
    print("--- Next action for Claude ---")
    next_action = {
        Phase.NEW: "Start by cd'ing into the worktree, reading the codebase, and asking clarifying questions.",
        Phase.READING_CODE: "Continue exploring the codebase, then ask clarifying questions.",
        Phase.BRAINSTORMING: "Finish formulating questions, then ask the user.",
        Phase.AWAITING_ANSWERS: "Ask the questions above to the user. When they answer, save progress and move to PLANNING.",
        Phase.PLANNING: "Write the implementation plan based on the answers above. Save progress and ask for approval.",
        Phase.AWAITING_APPROVAL: "Show the plan above to the user and ask if they approve. If yes, move to BUILDING.",
        Phase.BUILDING: "cd into the worktree and implement the plan. When done, save progress and push.",
        Phase.PUSHING: "Run push_branch.py to commit and push the branch.",
        Phase.DONE: "Nothing to do — this ticket is complete. The branch was pushed.",
        Phase.FAILED: "Review the error above. Decide whether to fix and retry, or abandon.",
    }
    print(next_action.get(state.phase, "Unknown phase, inspect the state file."))


if __name__ == "__main__":
    main()
