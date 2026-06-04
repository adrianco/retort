# Tasks

A **task** is what the agent is asked to build (and what gets scored). A task is
a directory (local or in a git repo) containing:

- `task.yaml` — functional spec, prompt, validation criteria, timeout
- `validate.py` — automated pass/fail validation script (optional)

## The registry

[`registry.yaml`](registry.yaml) indexes the known tasks. Each row maps a task
**name** to a canonical **source** URI:

```yaml
tasks:
  - name: rest-api-crud
    source: bundled://rest-api-crud          # lives in this repo, tasks/rest-api-crud/
  - name: brazil-bench
    source: github://brazil-bench/benchmark-template/brazilian-soccer-mcp-guide.md
```

List it any time:

```text
$ retort tasks list
NAME               SOURCE                                                                  TYPE
brazil-bench       github://brazil-bench/benchmark-template/brazilian-soccer-mcp-guide.md  github
cli-data-pipeline  bundled://cli-data-pipeline                                             local
react-dashboard    bundled://react-dashboard                                               local
rest-api-crud      bundled://rest-api-crud                                                 local

$ retort tasks show brazil-bench      # source + description
```

The bundled tasks ship in this repo; **brazil-bench** is the one task hosted
elsewhere (a public GitHub repo — a "Use this template" repo is the recommended
way to share one).

## Referencing a task

In `workspace.yaml` or `retort run --task`, use either a **registered name** or
an **explicit URI**:

```yaml
tasks:
  - source: brazil-bench                 # registered name (resolves via registry)
  - source: bundled://rest-api-crud      # explicit local
  - source: github://owner/repo/spec.md  # explicit GitHub source
```

A bare name resolves to its registry `source`. Explicit `scheme://` URIs
(`bundled://`, `local://`, `git://`, `github://`) are used verbatim.

## Adding a task

- **Bundled:** drop a `tasks/<name>/` dir with `task.yaml` (+ optional
  `validate.py`), then add a `source: bundled://<name>` row to `registry.yaml`.
- **Remote:** push the task to a GitHub repo (a template repo is ideal so others
  can fork it), then add a `source: github://<owner>/<repo>[/spec]` row.
