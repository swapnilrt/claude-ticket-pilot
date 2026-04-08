#!/usr/bin/env python3
"""Poll tracker for new comments on a ticket that is waiting for human input.

Checks every PLANE_POLL_INTERVAL seconds (default 120). When a new comment
is found, it advances the ticket phase and exits so the calling skill can
continue the workflow.

Usage: python poll_comments.py <ticket-key>

Exit codes:
  0 — new comment(s) detected, state advanced
  1 — error
  2 — usage / no state
  3 — ticket is not in a phase that waits for human input
  4 — timed out (exceeded PLANE_POLL_TIMEOUT)
"""
import os
import sys
import time

from _common import get_store, get_tracker


WAITING_PHASES = None  # populated after import


def check_for_comments(store, tracker, state):
    """Check tracker for comments newer than the last state update.

    Returns (new_comments, next_phase) or (None, None) if nothing new.
    """
    from ticket_state import Phase

    comments = tracker.get_comments(state.ticket_id)
    new_comments = [c for c in comments if c["created_at"] > state.updated_at]

    if not new_comments:
        return None, None

    if state.phase == Phase.AWAITING_ANSWERS:
        return new_comments, Phase.PLANNING
    elif state.phase == Phase.AWAITING_APPROVAL:
        # Any reply to an approval request is treated as approval feedback
        return new_comments, None  # special: handled by caller
    else:
        return new_comments, None


def main():
    if len(sys.argv) != 2:
        print("Usage: poll_comments.py <ticket-key>", file=sys.stderr)
        sys.exit(2)

    key = sys.argv[1]
    store = get_store()
    state = store.load(key)
    if state is None:
        print(f"ERROR: no state found for {key}.", file=sys.stderr)
        sys.exit(2)

    from ticket_state import Phase

    waiting_phases = {Phase.AWAITING_ANSWERS, Phase.AWAITING_APPROVAL}

    if state.phase not in waiting_phases:
        print(f"Ticket {key} is in phase '{state.phase.value}', not waiting for input.")
        sys.exit(3)

    interval = int(os.environ.get("PLANE_POLL_INTERVAL", "120"))
    timeout = int(os.environ.get("PLANE_POLL_TIMEOUT", "3600"))
    tracker = get_tracker()

    phase_label = state.phase.value
    max_attempts = max(1, timeout // interval)
    print(f"Polling tracker for comments on {key} (phase: {phase_label}, interval: {interval}s, timeout: {timeout}s, max attempts: {max_attempts})...")
    print(f"Press Ctrl+C to stop.\n")

    attempt = 0
    while attempt < max_attempts:
        try:
            new_comments, next_phase = check_for_comments(store, tracker, state)

            if new_comments:
                bodies = "\n\n".join(c["body"] for c in new_comments)
                print(f"[poll] Detected {len(new_comments)} new comment(s):\n")
                for c in new_comments:
                    print(f"  [{c['actor']}] {c['body'][:200]}")
                print()

                if state.phase == Phase.AWAITING_ANSWERS:
                    state.user_answers = bodies
                    state.phase = Phase.PLANNING
                    state.log("auto_received_answers", f"Polled {len(new_comments)} new comment(s) from tracker")
                    store.save(state)
                    print(f"=> Saved answers and advanced to 'planning'.")

                elif state.phase == Phase.AWAITING_APPROVAL:
                    # Check if the comment looks like approval
                    combined = bodies.lower()
                    if any(word in combined for word in ["yes", "approve", "approved", "lgtm", "go ahead", "ship it"]):
                        state.phase = Phase.BUILDING
                        state.log("auto_approved", f"Approval detected in tracker comment")
                        store.save(state)
                        print(f"=> Approval detected — advanced to 'building'.")
                    elif any(word in combined for word in ["no", "reject", "stop"]):
                        state.log("approval_rejected", f"Rejection detected in tracker comment")
                        store.save(state)
                        print(f"=> Rejection detected. Staying in 'awaiting_approval'. Review the feedback.")
                    else:
                        # Treat as feedback/changes requested
                        state.log("approval_feedback", bodies[:500])
                        store.save(state)
                        print(f"=> Feedback received. Staying in 'awaiting_approval' for plan revision.")

                sys.exit(0)

            # No new comments — wait and retry
            attempt += 1
            remaining = max_attempts - attempt
            sys.stdout.write(f"  [{time.strftime('%H:%M:%S')}] No new comments. Next check in {interval}s ({remaining} attempts left)...\r")
            sys.stdout.flush()
            time.sleep(interval)

            # Reload state in case another process updated it
            state = store.load(key)
            if state is None or state.phase not in waiting_phases:
                print(f"\nTicket state changed externally (now: {state.phase.value if state else 'deleted'}). Exiting.")
                sys.exit(0)

        except KeyboardInterrupt:
            print("\nStopped polling.")
            sys.exit(0)

    # Exhausted all attempts
    elapsed = max_attempts * interval
    print(f"\n[poll] Timed out after {elapsed}s ({max_attempts} attempts). No reply received on tracker.")
    state.log("poll_timeout", f"No reply after {elapsed}s ({max_attempts} attempts)")
    store.save(state)
    sys.exit(4)


if __name__ == "__main__":
    main()
