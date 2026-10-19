# Evaluation: agent=hermes-0222_language=rust_model=mlxlocal/bottlecapai--ThinkingCap-Qwen3.8-27B-MLX-4bit-DWQ_prompt=neutral_stack=tcap · rep 3

## Summary

- **Factors:** language=rust, agent=hermes-0222, model=mlxlocal/bottlecapai--ThinkingCap-Qwen3.8-27B-MLX-4bit-DWQ, prompt=neutral, stack=tcap (temp 0.6 / top_p 0.95 / top_k 20 / rep_penalty 1.0, context 262144, compaction threshold 0.9 — from `_effective_stack.json`)
- **Status:** ok (`_meta.json` succeeded=true; agent's own `hermes verify` green)
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`); prompt=neutral adds no checkable instructions
- **Tests:** 24 passed / 0 failed / 0 skipped (24 effective) — 5 unit (`src/lib.rs`) + 19 integration (`tests/integration.rs`); test_coverage=1.0 from `scores.json`
- **Build:** pass — defect_rate=1.0 from `scores.json` (not re-run)
- **Lint:** code_quality=0.833 from `scores.json` (maintainability 0.661, idiomatic 0.8)
- **Architecture:** see `summary/index.md`
- **Findings:** 5 items in `findings.jsonl` (0 critical, 0 high, 1 medium, 3 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates (title, author, year, isbn) | ✓ implemented | `src/lib.rs:149 create_book` → 201; test `create_book_returns_201_with_all_fields` |
| R2 | GET /books lists all | ✓ implemented | `src/lib.rs:174 list_books`; test `list_books_returns_all_books` |
| R3 | ?author= filter | ✓ implemented | `src/lib.rs:185-195` `WHERE author = ?1`; tests `list_books_filters_by_author`, `..._no_match_returns_empty` |
| R4 | GET /books/{id} (404 if absent) | ✓ implemented | `src/lib.rs:211 get_book`; tests `get_book_by_id_returns_book`, `get_book_not_found_returns_404` |
| R5 | PUT /books/{id} updates | ✓ implemented | `src/lib.rs:223 update_book` (partial update, 404/400); 4 update tests |
| R6 | DELETE /books/{id} | ✓ implemented | `src/lib.rs:261 delete_book` → 204/404; 2 delete tests |
| R7 | SQLite storage | ✓ implemented | `rusqlite` bundled (`Cargo.toml`), `src/lib.rs:99 init_db`, file `books.db` via `DATABASE_PATH` (`src/main.rs:11`) |
| R8 | JSON responses + status codes | ✓ implemented | `ApiError::into_response` `src/lib.rs:67`; 201/200/204/400/404 tested. Caveat: extractor rejections are text/plain (finding `json-rejection-not-json`) |
| R9 | title/author required | ✓ implemented | `src/lib.rs:80 validate_required` (missing and blank); tests `create_book_missing_title/author_returns_400`, `create_book_blank_title_returns_400`, `update_book_empty_author_returns_400` |
| R10 | GET /health | ✓ implemented | `src/lib.rs:144 health`; test `health_returns_ok` |
| R11 | README with setup/run | ✓ implemented | `README.md` Setup/Run/env-var table/curl examples (131 lines) |
| R12 | ≥3 tests | ✓ implemented | 24 tests, all pass (test_coverage=1.0) |

Enhancement beyond spec: `GET /` service descriptor (`src/lib.rs:133`), added to satisfy the verify readiness probe.

## Build & Test

Not re-run, per skill — stored scores used:

```text
scores.json: {"code_quality": 0.833, "token_efficiency": 0.0086, "test_coverage": 1.0, "defect_rate": 1.0, "maintainability": 0.661, "idiomatic": 0.8}
```

```text
agent's final `hermes verify --json` (from _agent_stdout.log): ok=true
build: cargo build exit 0, no warnings
test: 24/24 passed (5 unit + 19 integration)
boot + readiness: http://127.0.0.1:8000/ -> 200
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 362 (`src/lib.rs` 335 incl. 46 lines of unit tests, `src/main.rs` 27) |
| Test LOC | 294 (`tests/integration.rs`) |
| Files | 5 (2 src, 1 test, Cargo.toml, README.md) |
| Dependencies | 5 direct + 1 dev (70 packages in Cargo.lock) |
| Tests total | 24 |
| Tests effective | 24 |
| Skip ratio | 0% (`#[ignore]` count = 0) |
| Build duration | not measured (not re-run) |
| Agent tokens | 74,333 in / 21,804 out / 1,087,488 cache-read, 29 API calls (`.hermes_usage.json`) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [medium] Body-extractor rejections (malformed JSON, wrong types, missing Content-Type) return axum's text/plain bodies, not the `{"error":…}` envelope the README promises — `src/lib.rs:151`, `:226`.
2. [low] PUT cannot clear `year`/`isbn`: null ≡ omitted — `src/lib.rs:245-246`.
3. [low] PUT validation calls `validate_required` with `"placeholder"` arguments — `src/lib.rs:236-241`.
4. [low] `lock().unwrap()` in every handler; a poisoned mutex takes the service down — `src/lib.rs:159` et al.
5. [info] Extra `GET /` route beyond spec — `src/lib.rs:279`.

## Reproduce

```bash
cd "<run_dir>"
cat scores.json stack.json _meta.json _effective_stack.json
cat ../../../REQUIREMENTS.json ../../../prompts/neutral.md
grep -rnE "#\[ignore\]" src tests | wc -l
grep -nE "#\[(tokio::)?test" src/lib.rs tests/integration.rs | wc -l
wc -l src/*.rs tests/*.rs README.md
```
