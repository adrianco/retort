# Evaluation: effort=low language=erlang model=claude-haiku-5-5 prompt=neutral · rep 1

## Summary

- **Factors:** language=erlang, model=claude-haiku-5-5, effort=low, prompt=neutral (agent/framework=unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 18 passed / 0 failed / 0 skipped (18 effective) — from test_coverage=1.0
- **Build:** pass (test_coverage=1.0 from scores.json ⇒ build + tests ran)
- **Lint:** pass — code_quality=1.0 from scores.json (rebar built with `warnings_as_errors`)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

Scores read from `scores.json` (inline gate output): test_coverage=1.0, code_quality=1.0, defect_rate=1.0, maintainability=0.957, idiomatic=0.82, token_efficiency=0.0. Build/test/lint were NOT re-run per the evaluate-run skill.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `books_collection_handler.erl:23 create/1` → `books_db.erl insert/1`; test `create_and_fetch_book` |
| R2 | GET /books lists all books | ✓ implemented | `books_collection_handler.erl:16 list/1` → `books_db` list; test `list_and_filter_by_author` |
| R3 | GET /books ?author= filter | ✓ implemented | `books_collection_handler.erl:39 author_filter/1` + `books_db.erl:70` WHERE author COLLATE NOCASE |
| R4 | GET /books/{id}, 404 if absent | ✓ implemented | `books_item_handler.erl:16 dispatch GET` → 200/404; tests `create_and_fetch_book`, `unknown_ids_and_methods` |
| R5 | PUT /books/{id} updates | ✓ implemented | `books_item_handler.erl:19 dispatch PUT` → `books_db update/2`; test `update_replaces_book` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `books_item_handler.erl:34 dispatch DELETE` → 204; test `delete_removes_book` |
| R7 | Data in SQLite / embedded DB | ✓ implemented | `books_db.erl` esqlite3 open + schema; esqlite dep in rebar.config |
| R8 | JSON responses + correct status codes | ✓ implemented | `books_http.erl reply_json/3`; 201/200/204/400/404/405/503 across handlers |
| R9 | Validation: title & author required | ✓ implemented | `books_validate.erl required_string/2`; tests `missing_required_fields`, `create_rejects_invalid_input` |
| R10 | GET /health health check | ✓ implemented | `books_health_handler.erl` → pings DB, 200/503; test `health_check` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` (5.2 KB) present |
| R12 | ≥3 unit/integration tests | ✓ implemented | 18 tests (10 API + 8 validate); test_coverage=1.0 |

## Build & Test

Not re-run — stored scores used per evaluate-run skill step 2.

```text
scores.json: {"test_coverage": 1.0, "code_quality": 1.0, "defect_rate": 1.0,
              "maintainability": 0.9566, "idiomatic": 0.82, "token_efficiency": 0.0}
# test_coverage=1.0 ⇒ `rebar3 eunit` built the app and all tests passed.
# rebar.config sets warnings_as_errors, so a clean build is also lint-clean.
```

Test inventory (grepped, no skips found):
- `test/books_api_tests.erl` — 10 end-to-end HTTP tests via httpc against the live app
- `test/books_validate_tests.erl` — 8 unit tests for the validation module

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (src+test .erl) | 572 |
| Files (excl. _build/.git) | 22 |
| Dependencies | 2 (cowboy 2.12.0, esqlite 0.8.8) |
| Tests total | 18 |
| Tests effective | 18 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`) — all informational; nothing reduces the score:

1. [info] PUT uses full-replace semantics (omitted year/isbn reset to null)
2. [info] GET /books returns the full unpaginated collection (not required by spec)
3. [info] Author filter is exact case-insensitive match, not substring

## Reproduce

```bash
cd "experiments/adrianco/experiment-86-haiku55-alllang/rest-api-crud/runs/effort=low_language=erlang_model=claude-haiku-5-5_prompt=neutral/rep1"
cat scores.json          # stored mechanical scores (build/test/lint)
cat ../../REQUIREMENTS.json   # pinned 12-item checklist
grep -rnE "skip|xfail|disable" test/   # confirm no skipped tests
# To rebuild/test from scratch (NOT done during eval): rebar3 eunit
```
