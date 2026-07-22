# funkygibbon-port — Retort benchmark

**Task:** port the FunkyGibbon MCP client to a new programming language by
**extending an existing real codebase** ([the-goodies](https://github.com/adrianco/the-goodies)),
rather than building from scratch. This is the "hard, realistic" benchmark: the
agent must read a mature multi-language repo (Python + TypeScript reference
clients, ~30K lines, a shared protocol spec), find the right seams, and add a
third conformant client — sync engine + local graph cache + a 12-tool stdio MCP
server.

It is modelled on `brazil-bench` (a GitHub-hosted multi-file guide + fixtures),
but is harder because the deliverable lives inside a large existing repo and must
**interoperate on the wire** with the real server, not just satisfy a feature list.

## Contents

| File | Purpose |
|------|---------|
| `funkygibbon-mcp-port-guide.md` | The spec the agent reads (the "guide"). |
| `fixtures/version-strings.json` | Canonical version format/parse/order conformance cases. |
| `fixtures/knowledge-graph.json` | A small house graph used to seed the local-cache tool tests. |
| `fixtures/sync-exchanges.json` | Golden SyncRequest→SyncResponse pairs (full, delta, conflict, tombstone). |
| `fixtures/mcp-tool-golden.json` | Tool calls → expected results against the graph. |
| `REQUIREMENTS.json` | The pinned conformance checklist (R1–R12) for `requirement_coverage`. |
| `prompts.txt` | Prompt(s) used to drive runs. |
| `validate.py` | Light structural validation of the produced port. |

## Why it's a good Retort task

- **Language factor is the point.** The same spec is ported to each language in
  the experiment's `language` factor (Go, Rust, TypeScript, Elixir, …), so it
  directly measures "how reliably does model M get a *correct* inbetweenies port
  in language L."
- **Conformance, not vibes.** The fixtures pin objective pass/fail behaviour
  (version ordering, exclusive delta watermark, the 1-second version tiebreak,
  tombstones, the 12 tools), so the spec gate has a constant checklist across
  runs and languages.
- **Realistic difficulty.** Extending a large existing repo (find the protocol,
  the reference clients, the seams) exercises navigation + integration, not just
  greenfield generation.

## Running it

This is registered in `tasks/registry.yaml` as `funkygibbon-port`. Use it like
any task in `workspace.yaml` / `retort run --task`, e.g.:

```yaml
factors:
  language: [go, rust, typescript, elixir]
  model:    [claude-sonnet-4-6, claude-opus-4-8]
tasks:
  - source: funkygibbon-port
```

## Retort run model — PR on a worktree, not a copy (DESIGN, 2026-07-22)

This is a **large existing repo** (~30K lines), so the default playpen model —
`shutil.copytree` the support dir into every attempt, strip `.git`, `git init`
fresh — is wrong twice over: it makes N big copies AND destroys the base history a
port needs to diff against. Since the deliverable only *adds* a new top-level
directory, the natural unit of work and of storage is a **PR (a diff)**, not a
tree. Design:

1. **Base repo cloned ONCE, cached + pinned.** `the-goodies@v0.2.2` →
   `~/.retort/repos/the-goodies` (reference/bare clone). One deterministic base
   for every attempt and every language.
2. **Each attempt is a `git worktree`, not a copy.**
   `git worktree add <playpen> -b retort/<env_id> v0.2.2` — shares the base object
   store (no history duplication), and is a real git repo so the agent can commit
   and we can diff. The agent no longer self-clones; the repo is already checked
   out. **With local runs' `--parallel 1`, only one worktree exists at a time, so
   peak disk ≈ one checkout regardless of N** — this is what kills the "lots of big
   copies" problem. The worktree is `git worktree remove`d after scoring.
3. **The artifact is the PR, stored per attempt.** After the agent runs:
   `git add -A && git commit`, then `git format-patch v0.2.2..HEAD` →
   `runs/.../repN/attempt.patch` (+ the branch ref + commit sha). Tiny — just the
   port + its tests. **The archive stores the patch, never a copy of the-goodies.**
4. **Scored in the worktree, then torn down.** The fixtures/conformance tests and
   `test_coverage` run against the live worktree before removal; **`no_regression`
   runs the-goodies' own existing suite** (the Python/TS clients must still pass —
   the port must not break them), which is exactly what that gate is for.
5. **Winners → a real GitHub PR** *(chosen model)*. Every attempt is stored as a
   local patch/branch; additionally, the **promoted/winning attempt(s)** (e.g. the
   best rep per language, by req-coverage) push a branch and open a real PR on
   the-goodies via `gh` — provenance + review without N×reps of PR noise. Needs
   `gh` auth + write access; opening PRs is gated to promotion, not every run.

**Prompt change under this model:** the-goodies is *already* checked out in the
workspace — so drop the "clone it yourself" step; tell the agent to add its port
as a new top-level dir and NOT modify the existing clients.

**Retort changes needed (opt-in, greenfield tasks untouched):** a `base_repo:
{url, ref}` + `mode: repo-pr` in `task.yaml`; a worktree branch in
`LocalRunner.provision` (instead of `_copy_support_files`); a post-execute
commit → `format-patch` capture; `_archive_run_workspace` stores the patch for a
`repo-pr` task; and a promotion hook that opens the real PR on winners.

## Publishing as a GitHub template repo (brazil-bench style)

`brazil-bench` lives in a public "Use this template" repo and is referenced via
`github://`. To do the same here:

1. Create `adrianco/funkygibbon-port-bench` (a template repo).
2. Put `funkygibbon-mcp-port-guide.md`, `fixtures/`, and a top-level README in it.
3. Keep `REQUIREMENTS.json` here in retort (as brazil-bench does) — the registry
   `source` already points at `github://adrianco/funkygibbon-port-bench/funkygibbon-mcp-port-guide.md`.

Until that repo exists, switch the registry `source` to
`bundled://funkygibbon-port` to run it from this directory.
