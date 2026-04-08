---
name: ticket-pilot
description: Work on tickets end-to-end across Jira or Plane. Fetches a ticket by key, parses its embedded git config, creates a worktree, brainstorms with the user, plans, builds, and pushes a branch. Supports resumable single-ticket work and parallel multi-ticket dispatch across multiple terminals. Use when the user says "work on PROJ-12", "resume PROJ-12", "dispatch PROJ-12 PROJ-13", or "list tickets".
---

# Ticket Pilot

This skill drives a single ticket (from Jira or Plane) through brainstorm → plan → approve → build → push, with full state persistence so work can be paused and resumed across sessions. It also supports dispatching multiple tickets to parallel terminals.

## Required environment

The skill expects these environment variables to be set in the user's shell:

- `TRACKER_TYPE` (`plane`, `jira-cloud`, or `jira-server`)
- `TRACKER_BASE_URL` (e.g. `http://localhost:8080` or `https://your-org.atlassian.net`)
- `TRACKER_API_KEY`
- `TRACKER_PROJECT` (Plane: project UUID, Jira: project key like `PROJ`)

Optional:
- `TRACKER_WORKSPACE` (Plane workspace slug; not needed for Jira)
- `TRACKER_AUTH_TYPE` (`bearer` default, or `basic` for Jira basic auth)
- `TRACKER_USERNAME` (required if `TRACKER_AUTH_TYPE=basic`)
- `PLANE_POLL_INTERVAL` (seconds between tracker checks, default 120)
- `PLANE_POLL_TIMEOUT` (max seconds to wait for reply, default 3600)

If any are missing, the scripts will fail with a clear error. If you see such an error, tell the user which variable is missing and stop.

## Dispatching the right action

Read the user's request and decide which action they want:

| User says | Action |
|---|---|
| "work on PROJ-12", "start PROJ-12", "implement PROJ-12" | **Single ticket** flow (below) |
| "resume PROJ-12", "continue PROJ-12", "pick up PROJ-12" | **Resume** flow |
| "dispatch PROJ-12 PROJ-13 PROJ-14", "work on these in parallel: ..." | **Parallel** flow |
| "list tickets", "what am I working on", "show in-flight" | Run `list_tickets.py` |
| "status of PROJ-12" | Run `resume_ticket.py PROJ-12` (it prints a summary without changing state) |

If the user gives a single ticket key, always check whether state already exists for it before starting. The `start_ticket.py` script does this automatically and will tell you to resume if so.

---

## Single ticket flow

This is the main flow. It has two modes:

- **Interactive mode** (phases 1–4): All human communication happens via **tracker comments**. Claude posts questions and plans as comments, then polls for the user's reply. No chat interaction needed — the user responds on the tracker.
- **Autonomous mode** (phases 5–6): After the plan is approved, Claude builds, pushes, and comments **without any further human input**.

After each phase, **call `save_progress.py` to persist what just happened** — that's what makes the work resumable.

### Phase 1: Start

Run `python scripts/start_ticket.py <ticket-key>` and read its output carefully. The output gives you:
- The ticket title and description
- The repo URL and base branch
- The worktree path
- The branch name

**If `start_ticket.py` reports the ticket is already in state**, switch to the resume flow (load with `resume_ticket.py <ticket-key>` and continue from the reported phase).

**If `start_ticket.py` fails because the ticket has no `​```claude` config block**, stop and tell the user. Show them the format. Do not try to invent a repo URL.

### Phase 2: Read the codebase

`cd` into the worktree path printed by `start_ticket.py`. Use `ls`, `find`, and targeted `grep`/file reads to understand the area of the code the ticket touches. **Do not read the whole repo** — be focused. 5-15 file reads is usually enough.

After reading, save progress:
```
python scripts/save_progress.py <ticket-key> --phase brainstorming --event read_codebase
```

### Phase 3: Brainstorm questions (via tracker comment)

Formulate 3–6 clarifying questions for the user. Cover:
- Ambiguous requirements
- Existing patterns in the codebase the user wants you to follow
- Scope boundaries (what's explicitly out of scope)
- How to verify success (tests, manual check, both)

Save the questions, post them as a **comment on the ticket**, then **poll for the reply**:

```bash
cat > /tmp/q.txt <<'EOF'
1. Question one
2. Question two
...
EOF

python scripts/save_progress.py <ticket-key> --phase awaiting_answers \
  --from-file questions=/tmp/q.txt

python scripts/post_comment.py <ticket-key> --from-file /tmp/q.txt

python scripts/poll_comments.py <ticket-key>
```

The poller checks the tracker every `PLANE_POLL_INTERVAL` seconds (default 120, configurable in `.env`). When the user replies on the tracker, the poller saves the answers and advances to `planning`. **Do not ask the user in chat — The tracker is the communication channel.**

### Phase 4: Plan and get approval (via tracker comment)

After the poller exits (answers received), write a concrete implementation plan:
- Files to create or modify (with paths)
- Approach in 3-5 sentences
- Test strategy
- Open risks or assumptions

Save the plan, post it as a **comment on the ticket**, then **poll for approval**:

```bash
cat > /tmp/plan.md <<'EOF'
**Implementation Plan**

<your plan>

---
Approve this plan? Reply: **yes** / **changes needed: ...** / **no**
EOF

python scripts/save_progress.py <ticket-key> --phase awaiting_approval \
  --from-file plan=/tmp/plan.md

python scripts/post_comment.py <ticket-key> --from-file /tmp/plan.md

python scripts/poll_comments.py <ticket-key>
```

The poller recognizes:
- **Approval** ("yes", "approve", "lgtm", "go ahead", "ship it") → advances to `building`
- **Rejection** ("no", "reject", "stop") → stays in `awaiting_approval`, logged as rejected
- **Feedback** (anything else) → stays in `awaiting_approval`, logged as feedback for plan revision

If feedback is received, incorporate it, re-save the plan, re-post the updated plan as a comment, and poll again. Loop until approved or rejected.

### Phase 5: Build (autonomous)

**From here on, Claude runs autonomously — no human gates.**

```bash
python scripts/save_progress.py <ticket-key> --phase building --event approved
```

Make the actual code changes. Edit files directly in the worktree. Run any test commands relevant to the change. If tests fail, fix them before proceeding.

When the implementation is done, save a build summary:

```bash
cat > /tmp/summary.txt <<'EOF'
<short summary of what you built, files changed, tests run>
EOF

python scripts/save_progress.py <ticket-key> --phase pushing \
  --from-file build_summary=/tmp/summary.txt
```

### Phase 6: Push and comment (autonomous)

Push the branch:
```
python scripts/push_branch.py <ticket-key>
```

Then post a summary back to the ticket:
```bash
cat > /tmp/comment.md <<'EOF'
✅ **Build complete**

<build summary>

Pushed to branch `<branch-name>`. Ready for review.
EOF

python scripts/post_comment.py <ticket-key> --from-file /tmp/comment.md
```

The state file will now show `done`. Tell the user what branch was pushed and confirm the comment was posted.

---

## Resume flow

When the user says "resume PROJ-12":

1. Run `python scripts/resume_ticket.py <ticket-key>`. The script prints:
   - Current phase and what it means
   - The ticket description
   - Any previously-asked questions
   - Any previously-given answers
   - The plan (if it exists)
   - Recent history
   - **A "Next action" line telling you exactly what to do next**

2. Pick up at the indicated phase. For example:
   - If phase is `awaiting_answers` or `awaiting_approval`, run `poll_comments.py <ticket-key>` to wait for the tracker reply. (The resume script does a one-shot check first — if a reply already exists, it advances automatically.)
   - If phase is `building`, `cd` to the worktree and continue implementing autonomously.
   - If phase is `pushing`, run `push_branch.py` and `post_comment.py`.

3. Continue saving progress with `save_progress.py` as you advance phases. The state file is shared across sessions so this just works.

---

## Parallel dispatch flow

When the user gives multiple ticket keys:

1. Run `python scripts/dispatch_parallel.py <key1> <key2> <key3>`. The script:
   - Starts each ticket (or notes if already in state)
   - Prints a launch command per ticket for the user to run in separate terminals

2. Show the user the printed commands. **Tell them to open N new terminals** and paste each command. Each terminal becomes an independent Claude session working on one ticket.

3. **Do not try to drive multiple tickets from the current session**. Your job in dispatch mode ends after printing the launch commands. Each terminal session will use this same skill to resume its own ticket.

4. If the user wants to check on overall progress later, suggest `python scripts/list_tickets.py`.

---

## Status check

When the user asks "what am I working on" or "list tickets":

Run `python scripts/list_tickets.py` and show the user the table. Use `--all` to include completed tickets if they ask.

For a deep status check on one ticket, run `python scripts/resume_ticket.py <ticket-key>` — it prints the full state without changing anything.

---

## Rules

- **Never skip the approval gate.** Even if the ticket is small, ask for approval before building.
- **Never push to the base branch.** Always push to the `claude/<ticket-key>` branch the worktree was created on.
- **Never edit files outside the worktree.** All code changes happen inside the printed worktree path.
- **Save progress after every phase transition.** This is what makes the skill resumable. If you forget, the next session won't know where you are.
- **If a script exits non-zero, stop and tell the user.** Don't paper over errors with assumptions.
- **One ticket at a time per session.** If the user wants to work on multiple, use the parallel dispatch flow.
- **The user controls scope.** If they say "just fix the typo, no plan needed", you can move to building faster — but still save progress at each phase so resume works.

## Script reference

| Script | Purpose |
|---|---|
| `start_ticket.py <key>` | Fetch + parse + worktree + state init for one ticket |
| `resume_ticket.py <key>` | Print full state for resuming (no side effects) |
| `save_progress.py <key> --phase <p> [opts]` | Update state after a phase transition |
| `push_branch.py <key>` | Commit and push the worktree branch |
| `post_comment.py <key> "body"` | Post a comment to the ticket |
| `poll_comments.py <key>` | Poll tracker for new comments; advances phase when found |
| `list_tickets.py [--all]` | Show all tickets in state |
| `dispatch_parallel.py <key1> <key2> ...` | Set up multiple tickets and print launch commands |

All scripts live in `scripts/` relative to this skill's root. Run them with `python scripts/<name>.py ...` from the skill directory, or use the absolute path.
