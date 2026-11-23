# Evaluation: agent=codex effort=low language=objc model=gpt-6.2-sol prompt=neutral · rep 1

## Summary

- **Factors:** language=objc, model=gpt-6.2-sol, agent=codex, effort=low, prompt=neutral, framework=unknown
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** all passed / 0 failed / 0 skipped (4 scenario functions, ~30 assertions)
- **Build:** pass (test_coverage=1.0 from scores.json ⇒ build + tests succeeded; `-Wall -Wextra -Werror` clean)
- **Lint:** pass (code_quality=1.0 from scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 0 items in `findings.jsonl`

Scores (from `scores.json`): `test_coverage=1.0`, `code_quality=1.0`, `defect_rate=1.0`,
`maintainability=0.55`, `idiomatic=0.72`, `token_efficiency=0.048`.

A clean, idiomatic Objective-C implementation. The agent split transport (`Server.m`)
from domain logic (`Books.m`) behind a two-function header, which makes the handler a
pure `(db, method, target, body) -> response` function the tests drive directly against
SQLite. All twelve pinned requirements are satisfied with evidence; the toolchain built
warning-free under `-Werror` and every test passed.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `Books.m:115` `INSERT … RETURNING *`, returns 201 (`Books.m:154`); test `Tests.m:21` |
| R2 | GET /books lists all | ✓ implemented | `Books.m:123` `SELECT * FROM books ORDER BY id`; test `Tests.m:39` |
| R3 | GET /books ?author= filter | ✓ implemented | `Books.m:104-111` parse query, `Books.m:123` filtered SELECT; test `Tests.m:40` |
| R4 | GET /books/{id} single book | ✓ implemented | `Books.m:121` `SELECT … WHERE id=?`, 404 on miss (`Books.m:157`); test `Tests.m:25,31` |
| R5 | PUT /books/{id} update | ✓ implemented | `Books.m:117` `UPDATE … WHERE id=? RETURNING *`; test `Tests.m:26` |
| R6 | DELETE /books/{id} delete | ✓ implemented | `Books.m:119` `DELETE`, 204/404 via `sqlite3_changes` (`Books.m:157`); test `Tests.m:30,33` |
| R7 | SQLite storage | ✓ implemented | `Books.m:36` `InitializeBooks` CREATE TABLE, `Server.m:114` `sqlite3_open`; persistence test `Tests.m:61` |
| R8 | JSON responses + status codes | ✓ implemented | `Server.m:22-40` `SendResponse` (Content-Type application/json, reason phrases, Location); 200/201/204/400/404/405 used throughout |
| R9 | Validation: title & author required | ✓ implemented | `Books.m:43-62` `ValidBook` rejects blank/non-string → 400 (`Books.m:99`); tests `Tests.m:49-54` |
| R10 | GET /health | ✓ implemented | `Books.m:69-72` returns 200 `{"status":"ok"}`; test `Tests.m:47` |
| R11 | README with setup/run | ✓ implemented | `README.md` — build (`make`), run, route table, curl examples |
| R12 | ≥3 tests | ✓ implemented | `Tests.m` — 4 scenario functions (CRUD, filter, validation+health, persistence); test_coverage=1.0 |

### Enhancements beyond spec (not deductions)

- SQL-injection safety verified in tests (`Tests.m:42` — `' OR 1=1` treated as data).
- HTTP transport hardening: header/body size limits, `Transfer-Encoding` rejection,
  malformed `Content-Length` handling, send/recv timeouts (`Server.m`).
- On-disk persistence-across-reopen test (`Tests.m:61`), beyond the in-memory cases.
- Strict `year` validation (rejects booleans and non-safe-integers, `Books.m:52-59`).

## Build & Test

Not re-run — stored scores are authoritative per the evaluate-run skill.

```text
scores.json: test_coverage=1.0  ⇒ `make test` (clang build of Server.m+Books.m and
Tests.m+Books.m under -Wall -Wextra -Werror, then ./book-tests) built clean and all
assertions passed. Test binary prints:
  "PASS: validation and health, CRUD, author filtering, persistence"
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 415 (Books.h 5, Books.m 161, Server.m 162, Tests.m 87) |
| Files (source) | 6 (4 `.h`/`.m` + Makefile + README) |
| Dependencies | 3 system frameworks/libs (Foundation, CoreFoundation, sqlite3) |
| Tests total | 4 scenario functions (~30 assertions) |
| Tests effective | 4 (0 skipped) |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

None. All requirements implemented, tests pass, no skipped/disabled tests, lint clean.

## Reproduce

```bash
cd "experiments/adrianco/experiment-98-gpt62-sol-astra/rest-api-crud/runs/agent=codex_effort=low_language=objc_model=gpt-6.2-sol_prompt=neutral/rep1"
cat scores.json              # stored mechanical scores (build/test/lint)
make test                    # rebuild + run tests (clang, macOS SDK, sqlite3)
grep -nE "skip|xfail|DISABLED_" Tests.m   # → none
```
