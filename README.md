<p align="center">
  <h1 align="center">Claude Ticket Pilot</h1>
  <p align="center">
    <strong>Turn tickets into working code — autonomously.</strong>
  </p>
  <p align="center">
    A Claude Code skill that takes a Jira or Plane ticket and drives it through<br>
    brainstorm → plan → approve → build → push — with full state persistence,<br>
    parallel dispatch, and human-in-the-loop via tracker comments.
  </p>
  <p align="center">
    <a href="#quick-start">Quick Start</a> &bull;
    <a href="#how-it-works">How It Works</a> &bull;
    <a href="#supported-trackers">Supported Trackers</a> &bull;
    <a href="#configuration">Configuration</a> &bull;
    <a href="#contributing">Contributing</a>
  </p>
</p>

---

## Why

You have a ticket. You want Claude to implement it. But real engineering work isn't "write code" — it's read the ticket, understand the codebase, ask questions, get answers, plan, get approval, build, test, push. **Ticket Pilot automates the entire loop**, with you in control at every gate.

- **Resumable**: Crash mid-build? Close your laptop? Pick up exactly where you left off.
- **Comment-driven**: Claude posts questions and plans as tracker comments. You reply on Jira/Plane. Claude picks them up automatically.
- **Parallel**: Work on 5 tickets at once — each in its own terminal, its own worktree, its own state.
- **Tracker-agnostic**: Plane, Jira Cloud, Jira Server/Data Center. One skill, one config var to switch.

---

## Quick Start

### Install

```bash
# Add the marketplace
/plugin marketplace add swapnilrt/claude-ticket-pilot

# Install the plugin
/plugin install claude-ticket-pilot@swapnilrt-claude-ticket-pilot

# Reload plugins
/reload-plugins
```

The installer handles Python dependencies, configures your tracker connection interactively, and installs the [superpowers](https://github.com/anthropics/claude-plugins-official) dependency automatically.

### Add a spec block to your ticket

In your Jira or Plane ticket description, add:

````markdown
```claude
repo: git@github.com:yourorg/yourrepo.git
base_branch: main
```
````

### Go

```
claude "work on PROJ-12"
```

That's it. Claude fetches the ticket, clones the repo, reads the code, asks you questions (via tracker comments), writes a plan (via tracker comments), waits for your approval, builds it, runs tests, pushes a branch, and posts a summary back to the ticket.

---

## How It Works

### The Flow

```
┌─────────────────────────────────────────────────────────┐
│                    INTERACTIVE MODE                       │
│         (all communication via tracker comments)          │
│                                                           │
│  1. Start ──→ 2. Read Code ──→ 3. Ask Questions          │
│                                      │                    │
│                            ┌─── poll for reply ◄──┐      │
│                            ▼                      │      │
│                    4. Write Plan ──→ Post Plan     │      │
│                            │              │       │      │
│                            ▼         poll for     │      │
│                      Approved? ──no──► feedback ──┘      │
│                            │                              │
│                           yes                             │
├───────────────────────────┼───────────────────────────────┤
│                    AUTONOMOUS MODE                         │
│            (no human gates from here)                      │
│                            │                              │
│                    5. Build & Test                         │
│                            │                              │
│                    6. Push Branch                          │
│                            │                              │
│                    7. Post Summary                         │
│                            │                              │
│                          Done                             │
└───────────────────────────────────────────────────────────┘
```

### Modes

| You say | What happens |
|---|---|
| `work on PROJ-12` | Full flow: read ticket → ask questions → plan → approve → build → push |
| `resume PROJ-12` | Pick up exactly where the last session stopped |
| `dispatch PROJ-12 PROJ-13 PROJ-14` | Set up parallel terminals — one ticket per terminal |
| `list tickets` | Show all in-flight work with phase, title, branch |
| `status of PROJ-12` | Deep inspection without changing state |

### Resumability

Every phase transition is persisted to a JSON state file. The state file + git worktree together fully reconstruct an in-flight ticket. Close your laptop, kill the terminal, switch to a different task — `resume PROJ-12` picks up exactly where you were.

### Parallel Dispatch

Say `dispatch PROJ-12 PROJ-13 PROJ-14` and Ticket Pilot sets up isolated worktrees and prints launch commands. Paste each into a separate terminal. Each becomes an independent Claude session — real parallelism, real isolation, shared status view.

---

## Supported Trackers

| Tracker | Status | Auth Methods |
|---|---|---|
| **Plane** (self-hosted) | Supported | API key |
| **Jira Cloud** | Supported | Bearer token, Basic (email + API token) |
| **Jira Server / Data Center** | Supported | Bearer (PAT), Basic (username + password) |

Switching trackers is a single env var change (`TRACKER_TYPE`). The ticket spec block format adapts automatically — Plane uses HTML, Jira Cloud uses ADF, Jira Server uses wiki markup. All parsed transparently.

---

## Configuration

### Required

```bash
export TRACKER_TYPE=plane              # plane | jira-cloud | jira-server
export TRACKER_BASE_URL=http://localhost:8080
export TRACKER_API_KEY=your_api_key
export TRACKER_PROJECT=your_project_id # Plane: UUID, Jira: project key (e.g. PROJ)
```

### Tracker-Specific

```bash
# Plane only
export TRACKER_WORKSPACE=my-team

# Jira only
export TRACKER_AUTH_TYPE=bearer        # bearer (default) | basic
export TRACKER_USERNAME=you@email.com  # required for basic auth
```

### Polling (Comment-Driven Mode)

```bash
export PLANE_POLL_INTERVAL=120   # seconds between checks (default: 120)
export PLANE_POLL_TIMEOUT=3600   # give up after this many seconds (default: 3600)
```

### Optional Paths

```bash
export JIRA_SKILL_STATE=$HOME/.ticket-pilot/state
export JIRA_SKILL_REPOS=$HOME/.ticket-pilot/repos-cache
export JIRA_SKILL_WORKTREES=$HOME/.ticket-pilot/worktrees
```

> **Backward compatibility**: Existing `PLANE_*` environment variables (`PLANE_BASE_URL`, `PLANE_API_KEY`, `PLANE_WORKSPACE_SLUG`, `PLANE_PROJECT_ID`) continue to work. New installs should use `TRACKER_*`.

<details>
<summary><strong>Full configuration examples</strong></summary>

**Plane (self-hosted)**
```bash
export TRACKER_TYPE=plane
export TRACKER_BASE_URL=http://localhost:8080
export TRACKER_API_KEY=plane_api_xxxxxxxxxxxxxxxxxxxx
export TRACKER_WORKSPACE=my-team
export TRACKER_PROJECT=00000000-0000-0000-0000-000000000000
```

**Jira Cloud**
```bash
export TRACKER_TYPE=jira-cloud
export TRACKER_BASE_URL=https://yourorg.atlassian.net
export TRACKER_API_KEY=your_api_token
export TRACKER_AUTH_TYPE=bearer
export TRACKER_PROJECT=PROJ
```

**Jira Server / Data Center**
```bash
export TRACKER_TYPE=jira-server
export TRACKER_BASE_URL=https://jira.yourcompany.com
export TRACKER_API_KEY=your_personal_access_token
export TRACKER_AUTH_TYPE=basic
export TRACKER_USERNAME=your.username
export TRACKER_PROJECT=PROJ
```
</details>

---

## The Ticket Spec Block

Every ticket needs a `` ```claude `` config block in its description telling Claude which repo to work in.

**Plane / Jira Cloud** (fenced code block):

````markdown
```claude
repo: git@github.com:yourorg/yourrepo.git
base_branch: main
```
````

**Jira Server** (wiki markup):

```
{code:claude}
repo: git@github.com:yourorg/yourrepo.git
base_branch: main
{code}
```

| Field | Required | Default | Purpose |
|---|---|---|---|
| `repo` | yes | — | Git remote URL (SSH or HTTPS) |
| `base_branch` | no | `main` | Branch to work from |
| `branch_prefix` | no | `claude/` | Branch name prefix (`claude/issue-12`) |
| `working_dir` | no | repo root | Subdirectory for monorepos |
| `permission_mode` | no | `acceptEdits` | `acceptEdits` or `bypassPermissions` |
| `skip_brainstorm` | no | `false` | Skip clarifying questions, go straight to planning |

---

## Ideal Ticket Example

Here's a complete example of a well-structured ticket that Ticket Pilot can work on effectively. The more context you give, the fewer brainstorm questions Claude needs to ask and the better the plan will be.

---

### Add a greeting CLI tool with configurable messages

````markdown
```claude
repo: git@github.com:yourorg/hello-world-cli.git
base_branch: main
branch_prefix: claude/
```
````

#### Context

The repo currently contains a bare `main.py` that prints "Hello, World!" to stdout. It works but isn't configurable — every use case that needs a different greeting or a different target name has to edit the source. This ticket converts it into a proper CLI tool with argument parsing and a config file.

#### Goal

Turn the existing one-liner into a small CLI app that accepts a name and greeting via command-line args or a YAML config file. A user should be able to run `python main.py --name Alice` and get `Hello, Alice!` without touching any code.

#### Scope

##### `greeter.py` (the core module)

- A `Greeter` class with two settings: `greeting` (default: `"Hello"`) and `name` (default: `"World"`)
- A `greet()` method that returns the formatted string `"{greeting}, {name}!"`
- Loads defaults from `config.yaml` if present in the working directory
- CLI args override config file values, config file overrides hardcoded defaults

##### `main.py` (the CLI entry point)

- Uses `argparse` with `--greeting` and `--name` flags
- Instantiates `Greeter` with the resolved settings and prints the result
- Exit code 0 on success, 1 on invalid input

##### File layout

```
greeter.py          # Greeter class + config loading
main.py             # CLI entry point (argparse)
config.yaml         # example config file (committed with defaults)
tests/
  test_greeter.py   # unit tests
requirements.txt    # pyyaml
README.md           # updated with usage examples
```

##### Tests

- `test_greeter.py` covers:
  - Default greeting returns `"Hello, World!"`
  - Custom name returns `"Hello, Alice!"`
  - Custom greeting + name returns `"Hi, Bob!"`
  - Config file loading (use a temp file in the test)
  - CLI args override config values

#### Out of scope

- Internationalization / translation
- Web server or API mode
- Interactive prompts — CLI flags only
- Multiple output formats (JSON, etc.) — plain text only
- Logging framework — `print()` is fine
- Packaging / PyPI distribution

#### Acceptance criteria

- `python main.py` prints `Hello, World!` (backward compatible)
- `python main.py --name Alice` prints `Hello, Alice!`
- `python main.py --greeting Hi --name Bob` prints `Hi, Bob!`
- A `config.yaml` with `greeting: Hey` + `python main.py --name Alice` prints `Hey, Alice!`
- `python -m pytest tests/` passes with all tests green
- README documents all three usage modes (defaults, CLI args, config file)

#### Notes for the implementer

- Keep it simple — this is a CLI tool, not a framework. No plugin system, no dependency injection.
- Use `argparse` from the standard library, not click or typer.
- `pyyaml` is the only external dependency.
- The existing `main.py` is your starting point — refactor, don't rewrite from scratch.

---

### What makes a good ticket

| Element | Why it matters |
|---|---|
| **Clear title** | Claude uses it to understand scope at a glance |
| **Context section** | Explains the current state and why the change is needed |
| **Specific scope** | File-by-file breakdown so Claude knows exactly what to create or modify |
| **Out of scope** | Prevents Claude from over-engineering or drifting into unrelated changes |
| **Acceptance criteria** | Claude uses these to verify the implementation and write tests |
| **`claude` config block** | Required — tells Claude which repo, branch, and subdirectory to work in |
| **Implementer notes** | Guides Claude's judgment on style and library choices |

**Tips:**
- Structure tickets with Context → Goal → Scope → Out of scope → Acceptance criteria
- Be specific about behavior (`prints "Hello, Alice!"`) rather than vague (`handle names`)
- Mention existing patterns to follow (`use the same middleware pattern as auth.py`)
- List the file layout so Claude plans the right structure upfront
- If you want to skip brainstorming, add `skip_brainstorm: true` to the config block
- For monorepos, always set `working_dir` to narrow the codebase Claude reads

---

## Architecture

```
claude-ticket-pilot/
├── SKILL.md                      # Instructions Claude reads at runtime
├── plugin.json                   # Plugin manifest (name, version, dependencies)
├── post_install.py               # Interactive setup on install
├── requirements.txt              # requests, pyyaml
├── lib/
│   ├── tracker_adapter.py        # Abstract interface (TrackerAdapter ABC)
│   ├── plane_adapter.py          # Plane REST implementation
│   ├── jira_adapter.py           # Jira Cloud + Server REST implementation
│   ├── ticket_spec.py            # Parses ```claude blocks (markdown, HTML, ADF, wiki)
│   ├── ticket_state.py           # Per-ticket state machine (JSON persistence)
│   └── git_workspace.py          # Clone-on-demand + worktree management
├── scripts/
│   ├── _common.py                # Bootstrap: env vars, adapter factory, path helpers
│   ├── start_ticket.py           # Initialize ticket: fetch → parse → worktree → state
│   ├── resume_ticket.py          # Load state and print context for Claude
│   ├── save_progress.py          # Persist phase transitions
│   ├── push_branch.py            # Commit + push the feature branch
│   ├── post_comment.py           # Post a comment to the tracker
│   ├── poll_comments.py          # Watch for human replies via comments
│   ├── list_tickets.py           # Status table of all in-flight work
│   └── dispatch_parallel.py      # Multi-ticket parallel setup
└── test_skill.py                 # End-to-end test (fake tracker, dry-run git)
```

### Adapter Pattern

All tracker communication goes through `TrackerAdapter` (ABC). Adding a new tracker means implementing three methods:

```python
class YourTrackerAdapter(TrackerAdapter):
    def get_ticket_by_key(self, key: str) -> Ticket: ...
    def get_comments(self, issue_id: str) -> list[dict]: ...
    def add_comment(self, issue_id: str, body: str) -> str: ...
```

Register it in `_common.py`'s `get_tracker()` factory and you're done.

---

## Development

### Prerequisites

- Python 3.9+
- `requests` and `pyyaml` (`pip install -r requirements.txt`)

### Run Tests

```bash
python test_skill.py
```

Runs 12 stages through the full state machine with a fake tracker and dry-run git. No network, no real repos, no credentials needed. This is also the best way to understand how the scripts interact — the test exercises every one in order.

### Adding a New Tracker

1. Create `lib/your_adapter.py` implementing `TrackerAdapter`
2. Add a branch to `get_tracker()` in `scripts/_common.py`
3. Add a parser for your tracker's description format in `lib/ticket_spec.py`
4. Add a fake adapter in `test_skill.py` and run the tests

---

## Operational Notes

**One project at a time.** The skill talks to one tracker project per invocation (`TRACKER_PROJECT`). For multiple projects, use a shell function or alias that switches the env var.

**SSH access required.** Git clone runs as your local user. Repo URLs in ticket specs must be reachable via your SSH key or HTTPS credentials.

**State files are human-readable.** Named `ISSUE-12.json`, easy to inspect. Delete one to reset a stuck ticket.

**Worktrees persist after completion.** Deliberate — lets you revisit a "done" ticket's code. Clean up with `git worktree remove <path>`.

**Never pushes to main.** Always pushes to `claude/<ticket-key>`. Use branch protection on your base branch for extra safety.

**Crash recovery.** If a session dies mid-phase, `resume PROJ-12` shows exactly where things stand. The "next action" hint tells Claude what to do.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `required env var TRACKER_API_KEY is not set` | Missing env vars | Source your shell rc or export the variable |
| `No ```claude config block found` | Ticket missing spec block | Add a `` ```claude `` block to the description |
| `No ticket with sequence_id N` | Wrong project configured | Check `TRACKER_PROJECT` |
| `failed to create worktree: already exists` | Stale worktree from previous run | `resume` the ticket or `git worktree remove <path>` |
| Jira API returns 401 | Auth mismatch | Use `bearer` for Cloud, `basic` for Server. Check `TRACKER_USERNAME` for basic. |
| Jira API returns 403 on comment | Missing permission | Check "Add Comments" in Jira project permissions |
| Comment not appearing in tracker | UI lag | Check via API directly (see docs) |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, coding standards, and how to submit pull requests.

## Security

See [SECURITY.md](SECURITY.md) for reporting vulnerabilities.

## Acknowledgements

Built on top of [Superpowers](https://github.com/obra/superpowers) by Jesse Vincent — the skill library that teaches Claude brainstorming, planning, TDD, systematic debugging, and parallel dispatch. Ticket Pilot wouldn't exist without it.

## License

[MIT](LICENSE)
