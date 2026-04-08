"""Clone-on-demand + per-ticket worktrees."""
import os
import subprocess
from pathlib import Path

from ticket_spec import TicketSpec


class GitWorkspace:
    def __init__(self, repos_cache: Path, worktrees_root: Path):
        self.repos_cache = repos_cache
        self.worktrees_root = worktrees_root
        self.repos_cache.mkdir(parents=True, exist_ok=True)
        self.worktrees_root.mkdir(parents=True, exist_ok=True)
        self.dry_run = os.environ.get("GIT_DRY_RUN") == "1"

    def _ensure_clone(self, spec: TicketSpec) -> Path:
        repo_path = self.repos_cache / spec.repo_slug()
        if self.dry_run:
            repo_path.mkdir(parents=True, exist_ok=True)
            (repo_path / ".git").mkdir(exist_ok=True)
            return repo_path

        if not repo_path.exists():
            subprocess.run(["git", "clone", spec.repo, str(repo_path)], check=True)
        else:
            subprocess.run(["git", "fetch", "origin"], cwd=str(repo_path), check=True)
        return repo_path

    def create(self, ticket_key: str, spec: TicketSpec) -> tuple[Path, str]:
        repo_path = self._ensure_clone(spec)
        branch = f"{spec.branch_prefix}{ticket_key.lower()}"
        worktree = self.worktrees_root / spec.repo_slug() / ticket_key

        if self.dry_run:
            worktree.mkdir(parents=True, exist_ok=True)
            return worktree, branch

        if not worktree.exists():
            worktree.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                [
                    "git", "worktree", "add", "-b", branch, str(worktree),
                    f"origin/{spec.base_branch}",
                ],
                cwd=str(repo_path), check=True,
            )

        if spec.working_dir:
            return worktree / spec.working_dir, branch
        return worktree, branch

    def commit_and_push(self, worktree: Path, branch: str, message: str) -> None:
        if self.dry_run:
            print(f"[dry-run] would commit & push {branch} from {worktree}")
            return

        wt_root = worktree
        while not (wt_root / ".git").exists() and wt_root != wt_root.parent:
            wt_root = wt_root.parent

        subprocess.run(["git", "add", "-A"], cwd=str(wt_root), check=True)
        result = subprocess.run(
            ["git", "commit", "-m", message], cwd=str(wt_root), capture_output=True
        )
        if result.returncode != 0 and b"nothing to commit" not in result.stdout:
            raise RuntimeError(result.stderr.decode())
        subprocess.run(
            ["git", "push", "-u", "origin", branch], cwd=str(wt_root), check=True
        )
