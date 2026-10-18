# Evaluation: rest-api-crud · effort=low language=erlang model=claude-haiku-5-5 prompt=neutral · rep 2

## Summary

- **Factors:** language=erlang, model=claude-haiku-5-5, effort=low, prompt=neutral (agent/framework unknown in stack.json)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 25 passed / 0 failed / 0 skipped (25 effective) — `test_coverage=1.0` from scores.json
- **Build:** pass (`test_coverage=1.0`, `defect_rate=1.0` from scores.json; `warnings_as_errors` is set in rebar.config)
- **Lint:** pass — `code_quality=1.0` from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `src/books_http.erl:30 create_book` → `books_store.erl:create` |
| R2 | GET /books lists all | ✓ implemented | `src/books_http.erl:26 list_books` → `books_store:list/1` |
| R3 | GET /books ?author= filter | ✓ implemented | `src/books_http.erl:27 match_qs([author])`; `books_store.erl:matches_author` |
| R4 | GET /books/{id} single + 404 | ✓ implemented | `src/books_http.erl:36 item_request(GET)`; `not_found/1`; test `unknown_or_invalid_id_returns_404` |
| R5 | PUT /books/{id} updates | ✓ implemented | `src/books_http.erl:42 item_request(PUT)` → `books_store:update/2` (full-replace, see findings info) |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `src/books_http.erl:49 item_request(DELETE)` → 204; `books_store:delete/1` |
| R7 | SQLite / embedded DB | ✓ implemented | `src/books_store.erl:25 dets:open_file` — DETS disk-backed table; restart test |
| R8 | JSON responses + status codes | ✓ implemented | `src/books_http.erl:112 json_reply`; 201/200/204/400/404/405 used throughout |
| R9 | Validation: title & author required | ✓ implemented | `src/books_validate.erl:27 required_text` for title/author; test `create_rejects_missing_title` |
| R10 | GET /health | ✓ implemented | `src/books_http.erl:6 init(_, health)` → `{status: ok}`; test `health_returns_ok` |
| R11 | README with setup/run | ✓ implemented | `README.md` — Setup/Run/Test sections, endpoint + field tables, curl examples |
| R12 | ≥ 3 tests | ✓ implemented | 25 tests across 3 files; `test_coverage=1.0` |

## Build & Test

Scores read from `scores.json` (no re-run per evaluate-run skill):

```text
{"code_quality": 1.0, "token_efficiency": 0.0, "test_coverage": 1.0,
 "defect_rate": 1.0, "maintainability": 0.944, "idiomatic": 0.6}
```

`test_coverage=1.0` ⇒ build succeeded and all tests passed (rebar.config sets
`warnings_as_errors`, so the clean build also implies no compiler warnings).
No skip/ignore/todo markers found in `test/` (grep → 0).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 317 (5 modules + app.src) |
| Lines of code (tests) | 261 |
| Files (non-artifact) | 9 source/test + README + rebar config/lock |
| Dependencies (direct) | 1 (cowboy 2.12.0) |
| Tests total | 25 |
| Tests effective | 25 |
| Skip ratio | 0% |
| Build | pass (scores.json) |

## Findings

Top findings (full list in `findings.jsonl`) — all informational, no deductions:

1. [info] PUT /books/{id} is full-replace, not partial — documented in README, R5 satisfied
2. [info] Persistence survives restart, with explicit `books_survive_restart` test (exceeds R7)
3. [info] 405 Method Not Allowed with `Allow` header on known paths (robustness beyond spec)

## Reproduce

```bash
cd "experiments/adrianco/experiment-86-haiku55-alllang/rest-api-crud/runs/effort=low_language=erlang_model=claude-haiku-5-5_prompt=neutral/rep2"
cat scores.json                                   # stored build/test/lint scores
grep -rnE "skip|ignore|todo" test/                # skip detection (0 hits)
# Full verification (optional, not run here per evaluate-run skill):
#   rebar3 compile && rebar3 eunit
```
