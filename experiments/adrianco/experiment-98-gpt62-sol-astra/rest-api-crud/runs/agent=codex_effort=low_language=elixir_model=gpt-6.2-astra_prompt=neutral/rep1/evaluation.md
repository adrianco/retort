# Evaluation: agent=codex effort=low language=elixir model=gpt-6.2-astra prompt=neutral · rep 1

## Summary

- **Factors:** language=elixir, model=gpt-6.2-astra, agent=codex, effort=low, prompt=neutral, framework=unknown
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective) — from `test_coverage=1.0`
- **Build:** pass — from `defect_rate=1.0` / `test_coverage=1.0` (scores.json)
- **Lint:** pass — `code_quality=1.0` (scores.json)
- **Architecture:** run-summary skill unavailable in this session — see modules below
- **Findings:** 1 item in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `lib/router.ex:17-22`, `lib/store.ex:33-36`; year/isbn default to nil (`router.ex:55`) |
| R2 | GET /books lists all books | ✓ implemented | `lib/router.ex:12-15`, `lib/store.ex:18-31` (sorted by id) |
| R3 | GET /books ?author= filter | ✓ implemented | `lib/router.ex:13`, `lib/store.ex:22` exact-match filter; test `router.ex` list/filter |
| R4 | GET /books/{id} single book | ✓ implemented | `lib/router.ex:24-26`, `lib/store.ex:38-47`; 404 via `:missing` → `router.ex:85` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `lib/router.ex:28-30`, `lib/store.ex:52-53` (full replace, preserves id) |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `lib/router.ex:32-34`, `lib/store.ex:48-50`; 204 → `router.ex:86` |
| R7 | Data stored in embedded DB | ✓ implemented | `lib/store.ex:9` Erlang DETS (`:dets.open_file`), synced to disk (`store.ex:61`) |
| R8 | JSON responses + correct status codes | ✓ implemented | `router.ex:89-90` JSON helper; 201/200/204/404/400/422/413 across routes |
| R9 | Validation: title & author required | ✓ implemented | `lib/router.ex:77-83` `valid?/1` → 422 (`router.ex:60`); test at `books_test.exs:48-58` |
| R10 | GET /health health check | ✓ implemented | `lib/router.ex:8-10`; test `books_test.exs:60-64` |
| R11 | README.md with setup/run | ✓ implemented | `README.md` — deps.get/compile/run + endpoint table |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | `test/books_test.exs` — 4 tests; `test_coverage=1.0` |

## Build & Test

Scores read from `scores.json` (inline eval gate); build/test not re-run per skill policy.

```text
scores.json: {"code_quality": 1.0, "token_efficiency": 0.0, "test_coverage": 1.0,
              "defect_rate": 1.0, "maintainability": 0.8668, "idiomatic": 0.82}
```

- `test_coverage=1.0` ⇒ `mix compile` + all `mix test` cases passed.
- `code_quality=1.0` ⇒ lint clean.
- No skipped/disabled tests (`grep` for `@tag :skip`/`:pending` in `test/` → none).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, lib+config) | 181 |
| Files (excl. _build/deps/.git) | 18 |
| Dependencies | 2 (bandit, plug) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build duration | n/a (read from scores, not re-run) |

## Findings

Top items (full list in `findings.jsonl`):

1. [info] R9 validation rejects missing title/author with 422 (semantically correct) where the pinned `how_to_verify` cites 400 as its example — not a defect; malformed JSON still returns 400.

## Reproduce

```bash
cd "experiments/adrianco/experiment-98-gpt62-sol-astra/rest-api-crud/runs/agent=codex_effort=low_language=elixir_model=gpt-6.2-astra_prompt=neutral/rep1"
cat scores.json                                    # stored mechanical scores
cat ../../REQUIREMENTS.json                         # pinned 12-item checklist
grep -rEn "@tag :skip|:pending" test/               # skip detection → none
# To re-verify locally (not required): mix deps.get && mix test
```
