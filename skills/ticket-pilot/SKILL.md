---
name: ticket-pilot
description: Work on tickets end-to-end across Jira or Plane. Fetches a ticket by key, parses its embedded git config, creates a worktree, brainstorms with the user, plans, builds, and pushes a branch. Supports resumable single-ticket work and parallel multi-ticket dispatch across multiple terminals. Use when the user says "work on PROJ-12", "resume PROJ-12", "dispatch PROJ-12 PROJ-13", or "list tickets".
---

# Ticket Pilot

This skill drives a single ticket (from Jira or Plane) through brainstorm → plan → approve → build → push, with full state persistence so work can be paused and resumed across sessions. It also supports dispatching multiple tickets to parallel terminals.

## Plugin root

All scripts referenced below live in `scripts/` relative to the **plugin root**, not this skill file. The plugin root is two directories up from this SKILL.md.

**Before running any script**, find the plugin root and `cd` into it:

```bash
cd "$(find ~/.claude/plugins/cache -path "*/claude-ticket-pilot/*/scripts/check_env.py" -print -quit | xargs dirname | xargs dirname)"
```

**All `python scripts/...` commands below must be run from this directory.**

### Python compatibility

This skill works with **any Python 3.6+**. Use whatever `python3` is available. If `requests` is not installed, install it automatically:

```bash
python3 -c "import requests" 2>/dev/null || python3 -m pip install requests pyyaml -q
```

Run this once when you first start working. Do not ask the user to upgrade Python or install packages manually.

### Execution rules

**All scripts in this skill must be run WITHOUT asking the user for permission.** This includes:
- `check_env.py`, `setup_env.py`, `start_ticket.py`, `resume_ticket.py`
- `save_progress.py`, `post_comment.py`, `poll_comments.py`
- `push_branch.py`, `list_tickets.py`, `dispatch_parallel.py`

**Do NOT write temporary files.** Pass all text as inline arguments. Never use `cat > /tmp/...`, heredocs, or write to temp files — these trigger unnecessary permission prompts.

**Run poll_comments.py directly** without asking the user. It is a blocking call that waits for tracker replies — this is expected behavior, not something that needs user approval.

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

### Setup check (MUST run before any action)

**Before executing any command**, check whether the required environment variables are set by running:

```bash
python scripts/check_env.py
```

If `check_env.py` reports missing variables, **do not proceed with the user's request**. Instead, walk the user through setup:

1. Ask: **"Are you using Plane or Jira?"**
2. Based on their answer, ask only the relevant variables:

   **If Plane:**
   - `TRACKER_BASE_URL` — e.g. `http://localhost:8080`
   - `TRACKER_API_KEY` — their Plane API key
   - `TRACKER_WORKSPACE` — workspace slug
   - `TRACKER_PROJECT` — project UUID

   **If Jira Cloud:**
   - `TRACKER_BASE_URL` — e.g. `https://yourorg.atlassian.net`
   - `TRACKER_API_KEY` — API token
   - `TRACKER_PROJECT` — project key (e.g. `PROJ`)
   - `TRACKER_AUTH_TYPE` — ask: "Bearer token or basic auth?" (default: bearer)
   - If basic auth: `TRACKER_USERNAME` — their email

   **If Jira Server / Data Center:**
   - `TRACKER_BASE_URL` — e.g. `https://jira.yourcompany.com`
   - `TRACKER_API_KEY` — personal access token
   - `TRACKER_PROJECT` — project key (e.g. `PROJ`)
   - `TRACKER_AUTH_TYPE` — ask: "Bearer token or basic auth?" (default: bearer)
   - If basic auth: `TRACKER_USERNAME` — their username

3. Once you have all values, run `python scripts/setup_env.py` with the collected values to save them to the user's shell profile
4. Tell the user to restart their terminal or run `source ~/.zshrc` (or `~/.bashrc`) to pick up the new variables
5. Then proceed with the original request

If the user says "setup ticket-pilot" or "configure ticket-pilot", run the setup check directly.

### Reconfiguring

If the user says **"reconfigure ticket-pilot"**, re-run the full setup flow:

1. **Do NOT run `check_env.py` first.** The user wants to change their config regardless of current state.
2. Ask: **"Are you using Plane or Jira?"** (same flow as initial setup)
3. Collect the relevant variables
4. Run `python scripts/setup_env.py` with the new values — it will replace the existing config block in the shell profile
5. Tell the user to run `source ~/.zshrc` (or `~/.bashrc`)

## Dispatching the right action

Read the user's request and decide which action they want:

| User says | Action |
|---|---|
| "work on PROJ-12", "start PROJ-12", "implement PROJ-12" | **Single ticket** flow (below) |
| "resume PROJ-12", "continue PROJ-12", "pick up PROJ-12" | **Resume** flow |
| "dispatch PROJ-12 PROJ-13 PROJ-14", "work on these in parallel: ..." | **Parallel** flow |
| "list tickets", "what am I working on", "show in-flight" | Run `list_tickets.py` |
| "status of PROJ-12" | Run `resume_ticket.py PROJ-12` (it prints a summary without changing state) |
| "reconfigure ticket-pilot" | **Reconfigure** flow — re-prompts all tracker settings |

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

**Move the ticket to "In Progress"** (or equivalent) on the tracker:
```bash
python scripts/transition_ticket.py <ticket-key> --list
python scripts/transition_ticket.py <ticket-key> --to "In Progress"
```
If the transition fails (e.g. the status name is different), use `--list` to see available transitions and pick the closest match. If no "In Progress" equivalent exists, skip this step.

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
python scripts/save_progress.py <ticket-key> --phase awaiting_answers \
  --questions "1. Question one\n2. Question two\n..."

python scripts/post_comment.py <ticket-key> "1. Question one\n2. Question two\n..."

python scripts/poll_comments.py <ticket-key>
```

**Important: Pass text as inline arguments.** Do NOT use `cat > /tmp/...` or write temp files — that triggers unnecessary permission prompts.

The poller checks the tracker every `PLANE_POLL_INTERVAL` seconds (default 120, configurable in `.env`). When the user replies on the tracker, the poller saves the answers and advances to `planning`. **Do not ask the user in chat — The tracker is the communication channel.**

### Phase 4: Plan and get approval (via tracker comment)

After the poller exits (answers received), write a concrete implementation plan:
- Files to create or modify (with paths)
- Approach in 3-5 sentences
- Test strategy
- Open risks or assumptions

Save the plan, post it as a **comment on the ticket**, then **poll for approval**:

```bash
python scripts/save_progress.py <ticket-key> --phase awaiting_approval \
  --plan "<your plan text>"

python scripts/post_comment.py <ticket-key> "<your plan text>\n\n---\nApprove this plan? Reply: yes / changes needed: ... / no"

python scripts/poll_comments.py <ticket-key>
```

**Do NOT write temp files.** Pass all text as inline arguments.

The poller recognizes:
- **Approval** ("yes", "approve", "lgtm", "go ahead", "ship it") → advances to `building`
- **Rejection** ("no", "reject", "stop") → stays in `awaiting_approval`, logged as rejected
- **Feedback** (anything else) → stays in `awaiting_approval`, logged as feedback for plan revision

If feedback is received, incorporate it, re-save the plan, re-post the updated plan as a comment, and poll again. Loop until approved or rejected.

### Phase 5: Build (autonomous)

**From here on, Claude runs fully autonomously — NO human gates, NO permission prompts, NO asking the user for confirmation. Just build, test, and push.**

**CRITICAL: Before starting the build, set the permission mode to allow edits in the worktree without prompting:**

```bash
# Enable auto-edit mode so file changes don't trigger approval prompts
python scripts/save_progress.py <ticket-key> --phase building --event approved
```

**Autonomous execution checklist — do ALL of these without stopping:**
1. Edit files directly in the worktree — do NOT ask "should I proceed?" or "does this look right?"
2. Run tests — do NOT ask "should I run the tests?"
3. Fix any test failures — do NOT ask "should I fix this?"
4. Commit changes — do NOT ask "should I commit?"
5. Push the branch — do NOT ask "should I push?"
6. Post summary to tracker — do NOT ask "should I post?"

**If you find yourself about to type a question to the user during build/push, STOP — the answer is always "yes, proceed." The plan was already approved.**

Make the actual code changes. Edit files directly in the worktree. Run any test commands relevant to the change. If tests fail, fix them before proceeding.

**All commit messages must include the ticket key at the end.** For example: `Add validation to user input [PROJ-12]`. This applies to every commit made during the build phase.

When the implementation is done, save a build summary:

```bash
python scripts/save_progress.py <ticket-key> --phase pushing \
  --build-summary "<short summary of what you built, files changed, tests run>"
```

### Phase 6: Push and comment (autonomous)

**Continue autonomously — do not ask the user anything.**

Push the branch:
```
python scripts/push_branch.py <ticket-key>
```

Then post a summary back to the ticket:
```bash
python scripts/post_comment.py <ticket-key> "Build complete. <build summary>. Pushed to branch <branch-name>. Ready for review."
```

**Move the ticket to "In Review"** (or equivalent) on the tracker:
```bash
python scripts/transition_ticket.py <ticket-key> --to "In Review"
```
If "In Review" doesn't exist, try "Review", "Code Review", or use `--list` to find the right one. If no review status exists, skip this step.

The state file will now show `done`. Tell the user what branch was pushed, the ticket status was updated, and confirm the comment was posted.

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
- **After approval, run fully autonomously.** Do NOT ask the user for permission to edit files, run tests, commit, or push. The plan was approved — execute it end-to-end without stopping. Zero questions to the user from Phase 5 onwards. If you are about to ask the user anything during build or push, the answer is "yes" — just do it.
- **Never write temp files.** Pass all text as inline arguments to scripts. Do NOT use `cat > /tmp/...` or heredocs — they trigger unnecessary permission prompts.
- **Never push to the base branch.** Always push to the `claude/<ticket-key>` branch the worktree was created on.
- **Never edit files outside the worktree.** All code changes happen inside the printed worktree path.
- **Save progress after every phase transition.** This is what makes the skill resumable. If you forget, the next session won't know where you are.
- **If a script exits non-zero, stop and tell the user.** Don't paper over errors with assumptions.
- **One ticket at a time per session.** If the user wants to work on multiple, use the parallel dispatch flow.
- **The user controls scope.** If they say "just fix the typo, no plan needed", you can move to building faster — but still save progress at each phase so resume works.
- **Auto-install dependencies.** If `requests` or `pyyaml` is missing, install it silently with pip. Never ask the user to install Python packages or upgrade Python.

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
| `create_ticket.py --title T --description D` | Create a new ticket on the tracker |
| `transition_ticket.py <key> --to "Status"` | Move a ticket to a new status |
| `transition_ticket.py <key> --list` | List available status transitions |

All scripts live in `scripts/` relative to this skill's root. Run them with `python scripts/<name>.py ...` from the skill directory, or use the absolute path.
