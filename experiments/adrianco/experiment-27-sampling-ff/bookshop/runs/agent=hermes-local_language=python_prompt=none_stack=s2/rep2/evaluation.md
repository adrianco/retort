# Evaluation: agent=hermes-local language=python prompt=none stack=s2 · rep 2

## Summary

- **Factors:** language=python, agent=hermes-local (model Qwen3.6-35B-A3B), framework=unknown, prompt=none, stack=s2
- **Status:** cannot-verify — **all deliverable source files are absent from the archive** despite `_meta.json` `succeeded:true` and passing stored scores
- **Requirements:** 0/12 verifiable from the archive (12 cannot-verify) — see note below
- **Tests:** unverifiable from archive; `test_coverage=0.99` (scores.json) and stdout claims 16/16 passed, but `test_app.py` is not present and `.coverage` is empty (0 rows)
- **Build:** not evaluable — no source to build (stored `defect_rate=1.0` implies it built at score time)
- **Lint:** not evaluable — no source (stored `code_quality=0.789`)
- **Architecture:** no source in archive; `summary/` skipped
- **Findings:** 1 item in `findings.jsonl` (1 critical)

## The problem

The run directory contains only 8 files, every one of them metadata or a log:

```
.coverage (empty: 0 file/line_bits/arc rows)  .hermes_usage.json  TASK.md
_agent_stderr.log  _agent_stdout.log  _meta.json  scores.json  stack.json
```

There is **no `app.py`, `test_app.py`, `README.md`, or `requirements.txt`** — the four deliverables the task and the agent's own stdout describe. Sibling `rep1` (same cell) archives all of them plus `books.db`, `evaluation.md`, `findings.jsonl`, and `summary/`.

Evidence the code once existed and was scored:
- `scores.json`: `test_coverage=0.99`, `defect_rate=1.0`, `code_quality=0.789`, `maintainability=1.0` — these require source + a passing test run.
- `_agent_stdout.log`: "16/16 passed in 0.07s", enumerates `app.py`, `test_app.py`, `README.md`.
- `.hermes_usage.json`: `completed:true`, `failed:false`, 10 api_calls, 5942 output tokens.

So this is an **archive-integrity failure, not an agent-quality failure**: the workspace was populated and scored, then emptied before archival (the empty leftover `.coverage`, re-created at 15:49 with 0 rows, and `scores.json` written later at 15:54 are consistent with a post-run cleanup — most likely the stack-reload hook added in commit 131fbb8). The archive as it stands cannot be verified against the spec or reproduced.

## Requirements

The task ships a pinned checklist (`../../../REQUIREMENTS.json`, 12 items). None can be verified from the archive because the source is gone. Stored scores strongly suggest they were implemented and passing at score time, but that cannot be confirmed here.

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ? cannot-verify | no `app.py` in archive |
| R2 | GET /books lists books | ? cannot-verify | no `app.py` in archive |
| R3 | GET /books ?author= filter | ? cannot-verify | no `app.py` in archive |
| R4 | GET /books/{id} single book | ? cannot-verify | no `app.py` in archive |
| R5 | PUT /books/{id} update | ? cannot-verify | no `app.py` in archive |
| R6 | DELETE /books/{id} delete | ? cannot-verify | no `app.py` in archive |
| R7 | SQLite / embedded DB storage | ? cannot-verify | no `app.py`/`books.db` in archive |
| R8 | JSON responses + status codes | ? cannot-verify | no `app.py` in archive |
| R9 | Validation: title & author required | ? cannot-verify | no `app.py` in archive |
| R10 | GET /health endpoint | ? cannot-verify | no `app.py` in archive |
| R11 | README.md setup/run instructions | ? cannot-verify | no `README.md` in archive |
| R12 | ≥3 unit/integration tests | ? cannot-verify | no `test_app.py`; `.coverage` empty (stored `test_coverage=0.99`) |

## Build & Test

Not re-run (no source present). Stored mechanical scores from `scores.json`:

```text
test_coverage = 0.99   defect_rate = 1.0   code_quality = 0.789
maintainability = 1.0  idiomatic = 0.7     token_efficiency = 0.0192
```

`.coverage` DB present but empty:

```text
file=0  line_bits=0  arc=0   (coverage recorded nothing)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 0 (no source archived) |
| Files (excl. `__pycache__`) | 8 (all metadata/logs) |
| Dependencies | unknown (no `requirements.txt`) |
| Tests total | unknown (no `test_app.py`; stdout claims 16) |
| Tests effective | unknown |
| Skip ratio | n/a |
| Build duration | n/a |

## Findings

Full list in `findings.jsonl`:

1. [critical] Deliverable source, tests, and README absent from archived run — the workspace was scored (test_coverage=0.99) then emptied before archival; run is unverifiable and non-reproducible.

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiment-27-sampling-ff/bookshop/runs/agent=hermes-local_language=python_prompt=none_stack=s2/rep2
find . -type f -not -path "*/__pycache__/*" | sort        # only 8 metadata files
python3 -c "import sqlite3;c=sqlite3.connect('.coverage');print([ (t,c.execute(f'SELECT count(*) FROM {t}').fetchone()[0]) for t in ('file','line_bits','arc')])"
cat scores.json ; cat _agent_stdout.log                    # scored + 'files created', but none present
ls ../rep1                                                 # sibling archive is complete for contrast
```
