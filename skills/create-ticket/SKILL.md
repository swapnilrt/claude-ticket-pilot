---
name: create-ticket
description: Create a well-structured ticket on Jira or Plane from a natural language description. Use when the user says "create ticket for ...", "new ticket ...", or "create a task for ...".
---

# Create Ticket

This skill takes a natural language task description from the user and creates a well-structured ticket on their configured tracker (Jira or Plane), complete with the `claude` config block so Ticket Pilot can work on it immediately.

## Plugin root

Find the plugin root and `cd` into it before running any script:

```bash
cd "$(find ~/.claude/plugins/cache -path "*/claude-ticket-pilot/*/scripts/check_env.py" -print -quit | xargs dirname | xargs dirname)"
```

## Flow

When the user says "create ticket for ..." or "new ticket for ...":

### Step 1: Gather details

Ask the user the following questions **one at a time**:

1. **What needs to be done?** (if not already provided in their message)
2. **Which repo should this work in?** — git URL (SSH or HTTPS) or local path
3. **Base branch?** (default: `main`)
4. **Any additional context?** — existing patterns to follow, constraints, out-of-scope items (optional, user can skip)

### Step 2: Generate the ticket

Using the user's answers, generate a well-structured ticket with these sections:

```
# <Clear, concise title>

```
repo: <repo-url>
base_branch: <branch>
```

## Context

<1-2 sentences explaining the current state and why this change is needed>

## Goal

<1-2 sentences describing the desired outcome>

## Scope

<Bullet list of specific changes to make, organized by file or component>

### File layout (if creating new files)

<Tree structure of files to create/modify>

## Out of scope

<Bullet list of things explicitly NOT part of this task>

## Acceptance criteria

<Checklist of verifiable conditions that prove the work is done>

## Notes for the implementer

<Any style preferences, library constraints, or patterns to follow>
```

### Step 3: Confirm with user

Show the generated ticket to the user and ask: **"Does this look good? I'll create it on your tracker."**

If the user wants changes, revise and ask again. If they approve, proceed to Step 4.

### Step 4: Create the ticket

Run:

```bash
python scripts/create_ticket.py --title "<title>" --description "<full markdown description>"
```

Show the user the created ticket key (e.g. `SCRUM-15`) and confirm it's ready.

Optionally ask: **"Want me to start working on it now?"** — if yes, hand off to the ticket-pilot skill.

## Rules

- **Always include the code block with `repo:` in the description.** Without it, Ticket Pilot can't work on the ticket.
- **Keep titles short and action-oriented.** "Add rate limiting to /api/users" not "We need to add rate limiting to the users API endpoint because..."
- **Be specific in scope.** Name files, functions, and behaviors. Vague tickets produce vague plans.
- **Always include out-of-scope.** This prevents scope creep during the build phase.
- **Always include acceptance criteria.** These become the test plan.
- **Do NOT create the ticket without user confirmation.** Always show the draft first.
- **Pass text as inline arguments.** Do NOT write temp files.
- **NEVER delete files, directories, or data without explicit user permission.** This skill creates — it does not destroy.
