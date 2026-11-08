# Evaluation: agent=codex effort=low language=elixir model=gpt-6.1-terra prompt=neutral · rep 2

## Summary

- **Factors:** language=elixir, model=gpt-6.1-terra, agent=codex, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 5 passed / 0 failed / 0 skipped (5 effective)
- **Build:** pass — from scores.json (`test_coverage=1.0`, build is implicit in the test gate)
- **Lint:** pass — `code_quality=1.0` from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 1 item in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 1 info)

Stored scores (`scores.json`, inline gate): `test_coverage=1.0`, `code_quality=1.0`, `defect_rate=1.0`, `maintainability=0.939`, `idiomatic=0.8`, `token_efficiency=0.0`. `test_coverage=1.0` ⇒ build succeeded and all tests passed; not re-run here per skill guidance.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `lib/book_collection/router.ex:24` → `save(conn, %Book{}, 201)`; test `router_test.exs:27` |
| R2 | GET /books lists all books | ✓ implemented | `router.ex:14-22`; test `router_test.exs:44` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `router.ex:16-19` `where: b.author == ^author`; test `router_test.exs:45` |
| R4 | GET /books/{id} returns a single book (404 if absent) | ✓ implemented | `router.ex:28-30` + `with_book/3` 404 at `router.ex:58`; test `router_test.exs:32,38` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `router.ex:32-34` → `save(conn, book, 200)`; test `router_test.exs:33-36` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `router.ex:36-41` `Repo.delete!` → 204; test `router_test.exs:37` |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `repo.ex:2` `Ecto.Adapters.SQLite3`; `mix.exs` `ecto_sqlite3`; `config.exs:3-5` DB path |
| R8 | JSON responses with appropriate HTTP status codes | ✓ implemented | `json/3` `router.ex:70-72`; codes 200/201/204/404/400/422 across handlers (see info finding on 422) |
| R9 | Validation: title and author required | ✓ implemented | `book.ex:15` `validate_required([:title, :author])`; rejected via `save/3` `router.ex:64-66`; test `router_test.exs:54-57` |
| R10 | GET /health health-check endpoint | ✓ implemented | `router.ex:10-12` returns `{"status":"ok"}` 200; test `router_test.exs:20-24` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — deps.get, `mix run --no-halt`, env vars, API docs |
| R12 | At least 3 unit/integration tests | ✓ implemented | 5 tests in `test/router_test.exs`; `test_coverage=1.0` |

## Build & Test

Not re-run — stored mechanical scores are authoritative per `evaluate-run` step 2.

```text
scores.json: {"code_quality": 1.0, "test_coverage": 1.0, "defect_rate": 1.0,
              "maintainability": 0.939, "idiomatic": 0.8, "token_efficiency": 0.0}
# test_coverage=1.0 ⇒ `mix test` built and all 5 tests passed; defect_rate=1.0 ⇒ build+test OK
```

Test inventory (`grep`): 5 `test` blocks, 0 skip markers (`@tag :skip`, exclude, xtest → 0).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (lib+test+config, source only) | 177 |
| Files (excl. _build/deps/.git) | 18 |
| Dependencies (mix.exs) | 4 (bandit, plug, jason, ecto_sqlite3) |
| Tests total | 5 |
| Tests effective | 5 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run; inline-gate scores reused) |

## Findings

Full list in `findings.jsonl` (1 item):

1. [info] Validation errors return HTTP 422 rather than the spec-suggested 400 (`router.ex:66`). Defensible — 422 Unprocessable Entity is a standard code for validation failures and input is still rejected with a 4xx JSON error; malformed JSON does return 400 (`router.ex:50`). Noted for cross-run comparison, not a defect.

No critical/high/medium/low findings. This is a clean, fully-conformant run.

## Reproduce

```bash
cd "experiments/adrianco/experiment-93-terra61-deepen/rest-api-crud/runs/agent=codex_effort=low_language=elixir_model=gpt-6.1-terra_prompt=neutral/rep2"
cat scores.json                                  # stored mechanical scores (build+test gate)
cat ../../REQUIREMENTS.json                       # pinned 12-requirement checklist
grep -rcE "^\s*test " test/router_test.exs        # 5 tests
grep -rE "@tag :skip|:skip|xtest|exclude" test/   # 0 skips
# build/tests NOT re-run: test_coverage=1.0 already recorded by the inline eval gate
```
