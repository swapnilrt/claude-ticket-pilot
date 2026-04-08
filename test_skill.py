#!/usr/bin/env python3
"""End-to-end test of the skill scripts.

Strategy: monkey-patch PlaneAdapter to use a local JSON-backed fake before
each script runs. Uses GIT_DRY_RUN=1 so no real git operations happen.

Run with:
    python test_skill.py

You should see all stages drive a ticket through every phase, plus the
parallel dispatch and list scripts working correctly.
"""
import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent
TEST_ROOT = SKILL_ROOT / "_test_run"
SCRIPTS = SKILL_ROOT / "scripts"

# Set up test environment
os.environ["GIT_DRY_RUN"] = "1"
os.environ["JIRA_SKILL_STATE"] = str(TEST_ROOT / "state")
os.environ["JIRA_SKILL_REPOS"] = str(TEST_ROOT / "repos-cache")
os.environ["JIRA_SKILL_WORKTREES"] = str(TEST_ROOT / "worktrees")
# Set up test environment — new TRACKER_* vars
os.environ["TRACKER_TYPE"] = "plane"
os.environ["TRACKER_BASE_URL"] = "http://fake"
os.environ["TRACKER_API_KEY"] = "fake-key"
os.environ["TRACKER_WORKSPACE"] = "fake-ws"
os.environ["TRACKER_PROJECT"] = "fake-pid"
os.environ["PLANE_BASE_URL"] = "http://fake"
os.environ["PLANE_API_KEY"] = "fake-key"
os.environ["PLANE_WORKSPACE_SLUG"] = "fake-ws"
os.environ["PLANE_PROJECT_ID"] = "fake-pid"

# Fake Plane backend lives in a JSON file. Scripts read it via a
# monkey-patched PlaneAdapter that we inject as a sitecustomize.
FAKE_DB = TEST_ROOT / "fake_plane.json"
os.environ["FAKE_PLANE_DB"] = str(FAKE_DB)


def reset():
    if TEST_ROOT.exists():
        shutil.rmtree(TEST_ROOT)
    TEST_ROOT.mkdir()


def seed_tickets(tickets: list[dict]) -> None:
    FAKE_DB.write_text(json.dumps({"tickets": tickets, "comments": {}}, indent=2))


def install_fake_plane():
    """Write a sitecustomize.py that monkey-patches PlaneAdapter."""
    fake = TEST_ROOT / "sitecustomize.py"
    fake.write_text("""
import json
import os
import sys
from pathlib import Path

SKILL_LIB = Path(os.environ["SKILL_ROOT"]) / "lib"
sys.path.insert(0, str(SKILL_LIB))

from tracker_adapter import TrackerAdapter, Ticket

DB = Path(os.environ["FAKE_PLANE_DB"])

def _load():
    return json.loads(DB.read_text())

def _save(data):
    DB.write_text(json.dumps(data, indent=2))


class FakeTrackerAdapter(TrackerAdapter):
    def __init__(self, **kwargs):
        pass

    def get_ticket_by_id(self, issue_id):
        for t in _load()["tickets"]:
            if t["id"] == issue_id:
                return self._to_ticket(t)
        raise ValueError(f"no ticket {issue_id}")

    def get_ticket_by_key(self, key):
        seq = int(''.join(c for c in key if c.isdigit()))
        for t in _load()["tickets"]:
            if t["sequence_id"] == seq:
                return self._to_ticket(t)
        raise ValueError(f"no ticket {key}")

    def get_comments(self, issue_id):
        data = _load()
        return data["comments"].get(issue_id, [])

    def add_comment(self, issue_id, body):
        data = _load()
        data["comments"].setdefault(issue_id, []).append({"body": body})
        _save(data)
        return f"comment-{len(data['comments'][issue_id])}"

    def _to_ticket(self, t):
        return Ticket(
            id=t["id"],
            key=f"ISSUE-{t['sequence_id']}",
            name=t["name"],
            description=t["description"],
            label_names=t.get("labels", []),
        )


# Monkey-patch both old and new import paths
import plane_adapter as pa
pa.PlaneAdapter = FakeTrackerAdapter

import sys as _sys
import types
_fake_mod = types.ModuleType("jira_adapter")
_fake_mod.JiraAdapter = FakeTrackerAdapter
_sys.modules["jira_adapter"] = _fake_mod
""")
    return fake.parent


def run_script(script: str, *args, env_extra=None) -> tuple[int, str, str]:
    env = os.environ.copy()
    env["SKILL_ROOT"] = str(SKILL_ROOT)
    env["PYTHONPATH"] = str(TEST_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    if env_extra:
        env.update(env_extra)
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args],
        capture_output=True, text=True, env=env,
    )
    return result.returncode, result.stdout, result.stderr


def banner(msg):
    print(f"\n{'=' * 60}\n{msg}\n{'=' * 60}")


def must_succeed(rc, out, err, label):
    if rc != 0:
        print(f"FAIL: {label}")
        print(f"  stdout: {out}")
        print(f"  stderr: {err}")
        sys.exit(1)
    print(f"  ✓ {label}")


def main():
    reset()
    install_fake_plane()

    # Seed two tickets
    seed_tickets([
        {
            "id": str(uuid.uuid4()),
            "sequence_id": 12,
            "name": "Add CSV export",
            "description": """```claude
repo: git@github.com:swapnil/test.git
base_branch: main
```

Add a CSV export endpoint to the reports page.""",
            "labels": [],
        },
        {
            "id": str(uuid.uuid4()),
            "sequence_id": 13,
            "name": "Fix login bug",
            "description": """```claude
repo: git@github.com:swapnil/test.git
base_branch: main
```

Login fails when email contains a plus sign.""",
            "labels": [],
        },
    ])

    banner("STEP 1: start_ticket on PROJ-12")
    rc, out, err = run_script("start_ticket.py", "12")
    must_succeed(rc, out, err, "start_ticket.py 12")
    assert "ISSUE-12" in out, "expected ticket key in output"
    assert "Worktree:" in out, "expected worktree path in output"
    print("\n--- start_ticket.py output ---")
    print(out)

    banner("STEP 2: list_tickets shows ISSUE-12 as new")
    rc, out, err = run_script("list_tickets.py")
    must_succeed(rc, out, err, "list_tickets.py")
    assert "ISSUE-12" in out
    assert "new" in out
    print(out)

    banner("STEP 3: save_progress -> awaiting_answers")
    questions = "1. What columns?\n2. Encoding?\n3. Filter handling?"
    qfile = TEST_ROOT / "q.txt"
    qfile.write_text(questions)
    rc, out, err = run_script(
        "save_progress.py", "ISSUE-12", "--phase", "awaiting_answers",
        "--from-file", f"questions={qfile}",
    )
    must_succeed(rc, out, err, "save_progress -> awaiting_answers")
    assert "awaiting_answers" in out

    banner("STEP 4: simulate user answer, save -> planning -> awaiting_approval")
    answers = "All visible columns. UTF-8. Respect current filters."
    afile = TEST_ROOT / "a.txt"
    afile.write_text(answers)
    rc, out, err = run_script(
        "save_progress.py", "ISSUE-12", "--phase", "planning",
        "--from-file", f"answers={afile}",
    )
    must_succeed(rc, out, err, "save_progress -> planning")

    plan = "1. Add /reports/export.csv route\n2. Use existing query builder\n3. One unit test"
    pfile = TEST_ROOT / "p.txt"
    pfile.write_text(plan)
    rc, out, err = run_script(
        "save_progress.py", "ISSUE-12", "--phase", "awaiting_approval",
        "--from-file", f"plan={pfile}",
    )
    must_succeed(rc, out, err, "save_progress -> awaiting_approval")

    banner("STEP 5: resume_ticket should show full state with plan")
    rc, out, err = run_script("resume_ticket.py", "ISSUE-12")
    must_succeed(rc, out, err, "resume_ticket.py")
    assert "awaiting_approval" in out
    assert "What columns" in out
    assert "All visible columns" in out
    assert "/reports/export.csv" in out
    assert "Show the plan above" in out  # next-action hint
    print(out)

    banner("STEP 6: approve, build, save -> pushing")
    rc, out, err = run_script(
        "save_progress.py", "ISSUE-12", "--phase", "building", "--event", "approved",
    )
    must_succeed(rc, out, err, "save_progress -> building")

    summary = "Added route, added test, all green."
    sfile = TEST_ROOT / "s.txt"
    sfile.write_text(summary)
    rc, out, err = run_script(
        "save_progress.py", "ISSUE-12", "--phase", "pushing",
        "--from-file", f"build_summary={sfile}",
    )
    must_succeed(rc, out, err, "save_progress -> pushing")

    banner("STEP 7: push_branch (dry-run)")
    rc, out, err = run_script("push_branch.py", "ISSUE-12")
    must_succeed(rc, out, err, "push_branch.py")
    assert "pushed" in out.lower()

    banner("STEP 8: post_comment")
    cfile = TEST_ROOT / "c.txt"
    cfile.write_text("Built and pushed to claude/issue-12")
    rc, out, err = run_script("post_comment.py", "ISSUE-12", "--from-file", str(cfile))
    must_succeed(rc, out, err, "post_comment.py")

    # Verify comment was posted to the fake DB
    db = json.loads(FAKE_DB.read_text())
    assert len(db["comments"]) == 1
    print(f"  ✓ comment recorded in fake Plane")

    banner("STEP 9: list_tickets --all should show ISSUE-12 as done")
    rc, out, err = run_script("list_tickets.py", "--all")
    must_succeed(rc, out, err, "list_tickets.py --all")
    assert "done" in out
    print(out)

    banner("STEP 10: dispatch_parallel for 12 (already done) + 13 (fresh)")
    rc, out, err = run_script("dispatch_parallel.py", "12", "13")
    must_succeed(rc, out, err, "dispatch_parallel.py 12 13")
    assert "Already in state" in out, "expected ISSUE-12 to be detected as already started"
    assert "Terminal 1" in out
    assert "Terminal 2" in out
    assert "ISSUE-13" in out
    print(out)

    banner("STEP 11: resume an in-flight ticket simulating session crash")
    # ISSUE-13 was just started by dispatch_parallel; pretend we're a fresh
    # session and resume it
    rc, out, err = run_script("resume_ticket.py", "ISSUE-13")
    must_succeed(rc, out, err, "resume_ticket.py ISSUE-13")
    assert "new" in out
    assert "Login fails" in out  # description carried over
    print(out)

    banner("STEP 12: ticket_spec parses all four formats")
    sys.path.insert(0, str(SKILL_ROOT / "lib"))
    from ticket_spec import parse_ticket
    import json as json_mod

    # Markdown
    spec = parse_ticket("```claude\nrepo: git@github.com:x/y.git\n```\n\nDo stuff")
    assert spec.repo == "git@github.com:x/y.git", f"markdown failed: {spec.repo}"
    print("  ok markdown")

    # HTML (Plane)
    spec = parse_ticket('<pre><code class="language-claude">repo: git@github.com:x/y.git</code></pre>')
    assert spec.repo == "git@github.com:x/y.git", f"html failed: {spec.repo}"
    print("  ok html")

    # Wiki (Jira Server)
    spec = parse_ticket("{code:claude}repo: git@github.com:x/y.git{code}\n\nDo stuff")
    assert spec.repo == "git@github.com:x/y.git", f"wiki failed: {spec.repo}"
    print("  ok wiki")

    # ADF (Jira Cloud)
    adf = json_mod.dumps({"version": 1, "type": "doc", "content": [
        {"type": "codeBlock", "attrs": {"language": "claude"}, "content": [
            {"type": "text", "text": "repo: git@github.com:x/y.git"}
        ]}
    ]})
    spec = parse_ticket(adf)
    assert spec.repo == "git@github.com:x/y.git", f"adf failed: {spec.repo}"
    print("  ok adf")

    banner("✅ ALL STEPS PASSED")
    shutil.rmtree(TEST_ROOT)


if __name__ == "__main__":
    main()
