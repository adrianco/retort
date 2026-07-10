# Evaluation: agent=qwen3-coder-local_language=rust_prompt=neutral · rep 2

## Summary

- **Factors:** language=rust, agent=qwen3-coder-local, framework=actix-web, prompt=neutral
- **Status:** ok (one technical constraint unmet — storage is in-memory, not SQLite)
- **Requirements:** 11/12 implemented, 0 partial, 1 missing (R7 storage)
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective) — test_coverage=1.0 from scores.json
- **Build:** pass — test_coverage=1.0 ⇒ `cargo test` built and ran (not re-run)
- **Lint:** pass — code_quality=0.8333 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 1 high, 1 medium, 2 low)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `src/main.rs:46` `create_book`, returns 201 |
| R2 | GET /books lists all | ✓ implemented | `src/main.rs:77` `get_books` |
| R3 | GET /books ?author= filter | ✓ implemented | `src/main.rs:82-84` (substring `.contains`, see finding R3-substring) |
| R4 | GET /books/{id} by id | ✓ implemented | `src/main.rs:92-100`, 404 at `:99` |
| R5 | PUT /books/{id} update | ✓ implemented | `src/main.rs:103` `update_book`, 404 at `:128` |
| R6 | DELETE /books/{id} | ✓ implemented | `src/main.rs:132` `delete_book`, 204 at `:142`, 404 at `:140` |
| R7 | Data stored in SQLite/embedded DB | ✗ missing | `src/main.rs:37-40` in-memory `Mutex<Vec<Book>>`; no DB dep in Cargo.toml; README admits no DB |
| R8 | JSON responses + status codes | ✓ implemented | 201/200/404/204/400 via `HttpResponse::*().json()` |
| R9 | Validation: title & author required | ✓ implemented | `src/main.rs:48-54` (create only — see finding R9-partial-validation) |
| R10 | GET /health | ✓ implemented | `src/main.rs:42` `health`, route at `:221` |
| R11 | README with setup/run | ✓ implemented | `README.md` — build/run/test instructions present |
| R12 | ≥3 unit/integration tests | ✓ implemented | 3 `#[actix_web::test]` at `src/main.rs:152,165,200`; test_coverage=1.0 |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (inline gate).

```text
cargo test    # test_coverage = 1.0  ⇒ build succeeded and all 3 tests passed
```

```text
code_quality   = 0.8333   (lint)
defect_rate    = 0.8953
maintainability= 0.6456
idiomatic      = 0.48
token_efficiency = 0.0527
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 230 (`src/main.rs`) |
| Files (source) | 1 (`src/main.rs`) |
| Dependencies | 5 (actix-web, serde, serde_json, tokio, env_logger, lazy_static) |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [high] R7 — Data is not stored in SQLite or any embedded DB; in-memory `Vec`, lost on restart (`src/main.rs:37-40`).
2. [medium] Tests share a process-global mutable store, risking order-dependent flakiness (`src/main.rs:37-40`).
3. [low] `?author=` filter uses substring match, not exact author match (`src/main.rs:82-84`).
4. [low] Validation covers create only, not update (`src/main.rs:103-130`).

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiment-16-qwen3coder/bookshop-256k/runs/agent=qwen3-coder-local_language=rust_prompt=neutral/rep2
cat scores.json                 # mechanical scores (build/test/lint) — not re-run
grep -nE "Mutex<Vec<Book>>|sqlite|rusqlite|sqlx" src/main.rs Cargo.toml   # confirm no DB
grep -cE "#\[(actix_web::)?test\]" src/main.rs                            # 3 tests
```
