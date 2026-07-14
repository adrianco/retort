# Evaluation: agent=hermes-local_language=python_prompt=none_stack=s3 · rep 2

## Summary

- **Factors:** language=python, agent=hermes-local, framework=Flask (from stdout; stack.json says unknown), prompt=none, stack=s3
- **Status:** cannot-verify — **generated source, tests, and README are absent from the archived workspace.** Mechanical scores indicate the run built and passed tests, but no source remains to confirm requirements.
- **Requirements:** 1/12 implemented (R12 via stored coverage), 0 partial, 0 missing, 11 cannot-verify (source absent)
- **Tests:** 14 passed / 0 failed / 0 skipped per `_agent_stdout.log` — **not verifiable from the archive** (no `test_app.py`); `test_coverage=0.99` in scores.json confirms tests executed
- **Build:** pass (inferred) — `defect_rate=1.0`, `test_coverage=0.99` in scores.json (build + tests ran). Toolchain **not** re-run per skill policy.
- **Lint:** pass — `code_quality=0.789` in scores.json
- **Architecture:** summary skill **not run** — no source in the archive to summarize
- **Findings:** 3 items in `findings.jsonl` (1 critical, 0 high, 1 medium, 0 low, 1 info)

Scores read from `scores.json` (inline gate; rep2 is **not** in retort.db — only rep1 is):
`test_coverage=0.99`, `code_quality=0.789`, `defect_rate=1.0`, `maintainability=1.0`,
`idiomatic=0.4`, `token_efficiency=0.016`. Per skill policy the toolchain was **not** re-run.

**Anomaly (central finding):** `_meta.json` marks the run `succeeded: true` and the agent's
stdout claims it created `app.py`, `test_app.py`, and `README.md` with 14/14 tests passing —
yet none of those files are in the archive. The only run artifacts are metadata, logs, an
**empty** `.coverage` DB (0 file/line rows), and `.hermes_usage.json`. The sibling `rep1`
(identical cell) archived its full source. This is an archival/evaluation-integrity failure,
not (on the available evidence) a functional one — see `findings.jsonl` DELIV1.

## Requirements

Pinned `REQUIREMENTS.json` (12 items). Source is missing, so R1–R11 cannot be confirmed from
code; `test_coverage=0.99 > 0` directly attests R12.

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ? cannot-verify | source absent; stdout claims "create book", coverage passed |
| R2 | GET /books lists all | ? cannot-verify | source absent; stdout claims "list books" |
| R3 | GET /books ?author= filter | ? cannot-verify | source absent; stdout claims author filter |
| R4 | GET /books/{id} single (404) | ? cannot-verify | source absent; stdout claims get-by-id + 404 |
| R5 | PUT /books/{id} updates | ? cannot-verify | source absent; stdout claims update |
| R6 | DELETE /books/{id} deletes | ? cannot-verify | source absent; stdout claims delete |
| R7 | Data stored in SQLite | ? cannot-verify | source absent; no books.db archived either |
| R8 | JSON responses + status codes | ? cannot-verify | source absent; stdout claims 400/404/409 codes |
| R9 | Validation: title & author required | ? cannot-verify | source absent; stdout claims missing-title/author → 400 |
| R10 | GET /health endpoint | ? cannot-verify | source absent; stdout claims health check |
| R11 | README with setup/run | ✗ missing (from archive) | stdout claims README.md created; not present in run_dir |
| R12 | ≥3 unit/integration tests | ✓ implemented | `scores.json` test_coverage=0.99 > 0; stdout "14/14 passed" |

## Build & Test

Not re-run — no source to run, and stored scores used per skill policy.

```text
scores.json:        test_coverage=0.99  defect_rate=1.0  code_quality=0.789
_agent_stdout.log:  "Test results: 14/14 passed"  (health, CRUD, ?author=, 400 validation, 404, 409 dup-ISBN)
.coverage:          present (53KB) but EMPTY — 0 rows in file/line_bits/arc (coverage 7.15.1)
retort.db:          no experiment_runs row for python/s3/rep2 (only replicate 1)
archive source:     app.py / test_app.py / README.md ABSENT
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 0 (no source archived) |
| Source files (`*.py`/`*.md`, excl. TASK.md) | 0 |
| Total files in run_dir | 8 (all metadata/logs/artifacts) |
| Dependencies | unknown (no requirements.txt archived) |
| Tests total | 14 (per stdout; not in archive) |
| Tests effective | 14 (per stdout) |
| Skip ratio | 0% (per stdout; not verifiable) |
| Build duration | n/a (not re-run) |

## Findings

Full list in `findings.jsonl`.

1. [critical] DELIV1 — Archived workspace contains no source, tests, or README — deliverables absent (`find rep2/` shows only metadata; stdout claims files were created)
2. [medium] INTEG1 — Stored scores uncorroborated: `.coverage` empty (0 rows) and no retort.db row for rep2
3. [info] OBS1 — Mechanical scores (`defect_rate=1.0`, `test_coverage=0.99`) indicate the run built and passed tests; the defect is archival, not functional

## Reproduce

```bash
cd experiment-27-sampling-ff/bookshop/runs/agent=hermes-local_language=python_prompt=none_stack=s3/rep2
find . -type f | sort                      # only metadata/logs/artifacts — no source
cat scores.json                            # test_coverage=0.99 defect_rate=1.0
cat _agent_stdout.log                       # agent claims app.py/test_app.py/README.md + 14/14
python3 - <<'PY'                            # .coverage is empty
import sqlite3; c=sqlite3.connect('file:.coverage?mode=ro',uri=True)
print('file rows:', c.execute('SELECT count(*) FROM file').fetchone()[0])
PY
# compare with the well-formed sibling:
ls ../rep1                                 # app.py, test_app.py, README.md present
```
