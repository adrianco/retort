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

The agent should `git clone` the-goodies at the pinned tag (`v0.2.2`) into its
workspace and add the port as a new directory; the build/test step runs the
port's own tests.

## Publishing as a GitHub template repo (brazil-bench style)

`brazil-bench` lives in a public "Use this template" repo and is referenced via
`github://`. To do the same here:

1. Create `adrianco/funkygibbon-port-bench` (a template repo).
2. Put `funkygibbon-mcp-port-guide.md`, `fixtures/`, and a top-level README in it.
3. Keep `REQUIREMENTS.json` here in retort (as brazil-bench does) — the registry
   `source` already points at `github://adrianco/funkygibbon-port-bench/funkygibbon-mcp-port-guide.md`.

Until that repo exists, switch the registry `source` to
`bundled://funkygibbon-port` to run it from this directory.
