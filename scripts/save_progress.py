#!/usr/bin/env python3
"""Update the state file after a phase transition.

Usage:
    python save_progress.py <ticket-key> --phase <phase> [options]

Options:
    --questions TEXT      Brainstorm questions Claude asked
    --answers TEXT        User's answers to those questions
    --plan TEXT           Implementation plan
    --build-summary TEXT  Summary of what was built
    --error TEXT          Error message (sets phase to failed)
    --event TEXT          Event name to add to history (default: phase name)

Reads multi-line values from a file with --from-file <key>=<path>:
    python save_progress.py PROJ-12 --phase planning --from-file plan=/tmp/plan.md

Phases: new, reading_code, brainstorming, awaiting_answers, planning,
        awaiting_approval, building, pushing, done, failed
"""
import argparse
import sys
from pathlib import Path

from _common import get_store


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("ticket_key")
    parser.add_argument("--phase", required=True)
    parser.add_argument("--questions", default=None)
    parser.add_argument("--answers", default=None)
    parser.add_argument("--plan", default=None)
    parser.add_argument("--build-summary", default=None)
    parser.add_argument("--error", default=None)
    parser.add_argument("--event", default=None)
    parser.add_argument(
        "--from-file", action="append", default=[],
        help="Load a field from a file: --from-file plan=/tmp/plan.md",
    )
    args = parser.parse_args()

    store = get_store()
    state = store.load(args.ticket_key)
    if state is None:
        print(f"ERROR: no state for {args.ticket_key}", file=sys.stderr)
        sys.exit(1)

    from ticket_state import Phase
    try:
        new_phase = Phase(args.phase)
    except ValueError:
        valid = ", ".join(p.value for p in Phase)
        print(f"ERROR: invalid phase '{args.phase}'. Valid: {valid}", file=sys.stderr)
        sys.exit(2)

    # Apply file loads
    file_fields = {}
    for entry in args.from_file:
        if "=" not in entry:
            print(f"ERROR: --from-file expects key=path, got {entry}", file=sys.stderr)
            sys.exit(2)
        key, path = entry.split("=", 1)
        file_fields[key] = Path(path).read_text()

    # Apply updates
    if args.questions is not None:
        state.brainstorm_questions = args.questions
    if "questions" in file_fields:
        state.brainstorm_questions = file_fields["questions"]

    if args.answers is not None:
        state.user_answers = args.answers
    if "answers" in file_fields:
        state.user_answers = file_fields["answers"]

    if args.plan is not None:
        state.plan = args.plan
    if "plan" in file_fields:
        state.plan = file_fields["plan"]

    if args.build_summary is not None:
        state.build_summary = args.build_summary
    if "build_summary" in file_fields:
        state.build_summary = file_fields["build_summary"]

    if args.error is not None:
        state.error = args.error
        new_phase = Phase.FAILED

    state.phase = new_phase
    state.log(args.event or new_phase.value)
    store.save(state)

    print(f"OK: {args.ticket_key} -> {new_phase.value}")


if __name__ == "__main__":
    main()
