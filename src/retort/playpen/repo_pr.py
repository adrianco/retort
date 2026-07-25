"""repo-pr mode — work inside a large existing repo, deliver a PATCH.

For a task whose deliverable lands inside a big existing codebase (the
funkygibbon-port / the-goodies case: ~30K lines, the agent only ADDS a new
top-level directory), the default playpen model is wrong twice over: it
``copytree``s the whole repo into every attempt AND strips ``.git``, so there are
N big copies and no base history to diff against.

Here the unit of work and of storage is a **PR (a diff)**:

1. **One cached clone per repo** under ``~/.retort/repos/<owner>-<repo>``, pinned
   to ``base_ref`` — a single deterministic base for every attempt and language.
2. **Each attempt is a ``git worktree``**, which shares the cached clone's object
   store (no history duplication) and IS a real git repo, so the agent can commit
   and we can diff. Local runs are serial, so peak disk ≈ one checkout regardless
   of how many attempts run.
3. **The artifact is the patch**: after the agent finishes, commit everything and
   ``git format-patch <base_ref>..HEAD`` → ``attempt.patch``. Tiny (just the new
   code), and the archive never contains a copy of the base repo.
4. The worktree is removed after scoring; the patch + scores + logs survive.

Every function is best-effort and returns a status rather than raising, so a git
hiccup degrades the cell instead of aborting the grid.
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

REPO_CACHE = Path.home() / ".retort" / "repos"
PATCH_NAME = "attempt.patch"
# Files the patch-capture step must never commit as "the agent's work" — retort's
# own scaffolding, dropped into the worktree by provision().
_EXCLUDE = ("TASK.md", "stack.json", "prompts.txt", "REQUIREMENTS.json",
            "_agent_stdout.log", "_agent_stderr.log", ".hermes_usage.json",
            "_hermes_session.jsonl", PATCH_NAME)


def _git(*args: str, cwd: Path | None = None, timeout: int = 300):
    """Run git; return the CompletedProcess (never raises for a non-zero exit)."""
    try:
        return subprocess.run(
            ["git", *args], cwd=str(cwd) if cwd else None,
            capture_output=True, text=True, timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("git %s failed: %s", " ".join(args[:2]), exc)
        return None


def cache_slug(url: str) -> str:
    """A filesystem-safe cache dir name for a clone URL."""
    s = re.sub(r"^https?://|^git@|\.git$", "", url).replace(":", "/")
    return "-".join(p for p in s.split("/") if p)[-100:]


def ensure_base_clone(url: str, ref: str = "") -> Path | None:
    """Clone ``url`` once into the cache (or reuse it) and make ``ref`` available.

    Returns the clone path, or None if the clone could not be prepared. A pinned
    ``ref`` is fetched explicitly so a shallow default branch still resolves it.
    """
    REPO_CACHE.mkdir(parents=True, exist_ok=True)
    dest = REPO_CACHE / cache_slug(url)
    if not (dest / ".git").is_dir():
        logger.info("repo-pr: cloning base repo %s → %s", url, dest)
        r = _git("clone", "--no-checkout", url, str(dest), timeout=1800)
        if r is None or r.returncode != 0:
            logger.warning("repo-pr: clone failed: %s", (r.stderr if r else "")[-300:])
            shutil.rmtree(dest, ignore_errors=True)
            return None
    if ref:
        # Fetch the pinned ref (tag or branch) so worktree-add can resolve it.
        _git("fetch", "--tags", "origin", ref, cwd=dest, timeout=900)
        if _git("rev-parse", "--verify", f"{ref}^{{commit}}", cwd=dest) is None:
            return None
    return dest


def add_worktree(base: Path, target: Path, ref: str, branch: str) -> bool:
    """Check ``ref`` out at ``target`` as a worktree on a new ``branch``."""
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not any(target.iterdir()):
        target.rmdir()          # worktree add needs a missing or empty path
    r = _git("worktree", "add", "-b", branch, str(target), ref or "HEAD",
             cwd=base, timeout=900)
    if r is None or r.returncode != 0:
        logger.warning("repo-pr: worktree add failed: %s", (r.stderr if r else "")[-300:])
        return False
    return True


def capture_patch(worktree: Path, base_ref: str) -> Path | None:
    """Commit the agent's work and write ``attempt.patch`` (the deliverable).

    Retort's own scaffolding (TASK.md, stack.json, logs …) is excluded so the patch
    is just the agent's code. Returns the patch path, or None when the agent
    changed nothing.
    """
    # Stage everything, then UNSTAGE retort's scaffolding. (Writing
    # `.git/info/exclude` does not work here: in a worktree `.git` is a FILE
    # pointing at the real git dir inside the cached clone, so that path doesn't
    # exist and the scaffolding would end up committed as "the agent's work".)
    _git("add", "-A", cwd=worktree)
    _git("reset", "--quiet", "--", *_EXCLUDE, cwd=worktree)

    staged = _git("diff", "--cached", "--name-only", cwd=worktree)
    if staged is None or not (staged.stdout or "").strip():
        logger.info("repo-pr: agent produced no committable change")
        return None
    _git("-c", "user.email=retort@localhost", "-c", "user.name=retort",
         "commit", "--quiet", "-m", "retort: agent attempt", cwd=worktree)

    rng = f"{base_ref}..HEAD" if base_ref else "HEAD^..HEAD"
    r = _git("format-patch", rng, "--stdout", cwd=worktree, timeout=600)
    if r is None or r.returncode != 0 or not (r.stdout or "").strip():
        logger.warning("repo-pr: format-patch produced nothing")
        return None
    out = worktree / PATCH_NAME
    try:
        out.write_text(r.stdout)
    except OSError:
        return None
    logger.info("repo-pr: captured %s (%d bytes)", PATCH_NAME, len(r.stdout))
    return out


def remove_worktree(base: Path, target: Path) -> None:
    """Drop the worktree (after scoring). Best-effort."""
    _git("worktree", "remove", "--force", str(target), cwd=base, timeout=300)
    if target.exists():
        shutil.rmtree(target, ignore_errors=True)
