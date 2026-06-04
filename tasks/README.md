# Tasks

A **task** is what the agent is asked to build (and what gets scored). Every
task's canonical home is a **GitHub template repository** — a repo with
"Use this template" enabled, so creating a new task is a fork. A task repo (or
local mirror dir) contains:

- `task.yaml` — functional spec, prompt, validation criteria, timeout
- `validate.py` — automated pass/fail validation script (optional)

## The registry

[`registry.yaml`](registry.yaml) is the index of known tasks. Each row maps a
task **name** to its GitHub **template** and an optional **local** mirror under
this directory:

```yaml
tasks:
  - name: rest-api-crud
    template: github://adrianco/retort-task-rest-api-crud
    local: rest-api-crud          # offline mirror, preferred when present
  - name: brazil-bench
    template: github://brazil-bench/benchmark-template/brazilian-soccer-mcp-guide.md
    local: null                   # no mirror — loads live from GitHub
```

List it any time:

```text
$ retort tasks list
NAME               SOURCE (github template)                                                LOCAL
brazil-bench       github://brazil-bench/benchmark-template/brazilian-soccer-mcp-guide.md  —
cli-data-pipeline  github://adrianco/retort-task-cli-data-pipeline                         ✓ (fallback)
react-dashboard    github://adrianco/retort-task-react-dashboard                           ✓ (fallback)
rest-api-crud      github://adrianco/retort-task-rest-api-crud                             ✓ (fallback)

$ retort tasks show brazil-bench      # resolved source + description
```

## Referencing a task

In `workspace.yaml` or `retort run --task`, use either a **registered name** or
an **explicit URI**:

```yaml
tasks:
  - source: brazil-bench                 # registered name (resolves via registry)
  - source: bundled://rest-api-crud      # explicit local
  - source: github://owner/repo/spec.md  # explicit GitHub template
```

**Resolution order** for a bare name: the local mirror is used if present
(fast, offline), otherwise the task loads live from its GitHub `template`. An
explicit `scheme://` URI (`bundled://`, `local://`, `git://`, `github://`) is
always used verbatim.

## Adding a task

1. Publish a GitHub **template** repo containing `task.yaml` (+ optional
   `validate.py` and any fixtures the spec references).
2. Add a row to `registry.yaml` with its `template:` URL.
3. Optionally drop a `local:` mirror dir here so it runs offline.

> The `adrianco/retort-task-*` templates above are the canonical homes for the
> bundled tasks; until they're published they resolve to their local mirror.
