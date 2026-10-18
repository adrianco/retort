# Evaluation: rest-api-crud · rust / codex / gpt-6-luna / effort=low · rep 3

> **Second opinion.** This re-checks a prior evaluation that scored
> `requirement_coverage=0.75` and flagged R4/R5/R6 as not met due to an axum
> 0.7 route-syntax bug. **Verdict: the first evaluation was CORRECT on all three
> claims.** The handlers for R4/R5/R6 *are* present in the code (so nothing was
> invented), but the routes are genuinely unreachable at runtime, confirmed by
> the scorer's `test_coverage=0.333`. Coverage re-scored at **0.75 (9/12)**.

## Summary

- **Factors:** language=rust, agent=codex, model=gpt-6-luna, effort=low, prompt=neutral
- **Status:** failed (test gate — `test_coverage=0.333`, 1 of 3 tests pass)
- **Requirements:** 9/12 implemented, 3 partial (R4/R5/R6), 0 missing
- **Tests:** 1 passed / 2 failed / 0 skipped (3 effective)
- **Build:** pass — compiles clean (`defect_rate=1.0`, clippy clean per `code_quality=0.611`)
- **Lint:** pass — no warnings observed
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (4 high)

## Second-opinion re-check of the disputed claims

| Claim | First evaluator said | Re-check result |
|---|---|---|
| R4 GET /books/{id} | handler present, route unreachable (404) | **CONFIRMED.** `get_book` at `src/main.rs:91`, route `src/main.rs:118`. axum 0.7.9 / matchit 0.7.3 (Cargo.lock) treat `{id}` as literal. |
| R5 PUT /books/{id} | handler present, route unreachable | **CONFIRMED.** `update_book` at `src/main.rs:97`, same route, same cause. |
| R6 DELETE /books/{id} | handler present, route unreachable | **CONFIRMED.** `delete_book` at `src/main.rs:106`, same route, same cause. |

The first evaluator did **not** claim these were missing — it classified them as
*partial* (implemented but unreachable), which is accurate. The handlers exist;
the `{id}` route syntax is from axum 0.8 while `Cargo.toml` pins `axum = "0.7"`
(resolved to 0.7.9 in `Cargo.lock`). Under matchit 0.7.3, path params use `:id`
and `{id}` is a literal segment, so `/books/1` returns 404.

**Decisive empirical corroboration:** the scorer built with dependencies
available and recorded `test_coverage=0.333` — exactly 1 of 3 tests passing. The
only passing test (`validates_required_fields_and_filters_by_author`,
`src/main.rs:168`) is the only one that never hits an id-route. If the routes
matched, all three tests would pass and coverage would be 1.0. This is a GENUINE
bug, not a harness/tooling artefact (`defect_rate=1.0` shows clean compilation).

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `create_book` `src/main.rs:70`; route `src/main.rs:117` |
| R2 | GET /books lists all | ✓ implemented | `list_books` `src/main.rs:80`; route `src/main.rs:117` |
| R3 | GET /books ?author= filter | ✓ implemented | `BookFilter` `src/main.rs:34`, `src/main.rs:81`; test passes `src/main.rs:168` |
| R4 | GET /books/{id} by id | ~ partial | `get_book` `src/main.rs:91` present but route unreachable (axum 0.7 `{id}` literal, `src/main.rs:118`) |
| R5 | PUT /books/{id} update | ~ partial | `update_book` `src/main.rs:97` present but route unreachable |
| R6 | DELETE /books/{id} delete | ~ partial | `delete_book` `src/main.rs:106` present but route unreachable |
| R7 | SQLite storage | ✓ implemented | sqlx sqlite pool + `CREATE TABLE books` `src/main.rs:124` |
| R8 | JSON responses + status codes | ✓ implemented | `ApiError`/`IntoResponse` `src/main.rs:46`, 201/400/404/500/204 |
| R9 | Validate title & author required | ✓ implemented | `validate` `src/main.rs:64`; 400 test passes `src/main.rs:171` |
| R10 | GET /health | ✓ implemented | `health` `src/main.rs:112`; route `src/main.rs:117` |
| R11 | README with setup/run | ✓ implemented | `README.md` (run, endpoints, tests) |
| R12 | ≥3 tests that run | ✓ implemented | 3 `#[tokio::test]` fns; `test_coverage=0.333 > 0` so they run |

**requirement_coverage = 9 / 12 = 0.75**

(R12's pinned criterion is ">=3 tests exist and run (test_coverage > 0)", which is
satisfied — the 2 test *failures* are scored on the separate test-gate axis, not here.)

## Build & Test

Not re-run — stored scores used per the evaluate-run skill.

```text
scores.json: test_coverage=0.333  defect_rate=1.0  code_quality=0.611
             maintainability=0.667  idiomatic=0.42  token_efficiency=0.027
```

Interpretation: build compiles clean (defect_rate=1.0); 1 of 3 tests pass
(test_coverage=0.333). The agent could not self-verify — `cargo test` failed
offline with `Couldn't resolve host: index.crates.io` (`_agent_stdout.log`), so
it shipped unverified code.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 189 (`src/main.rs`) |
| Files | 4 (main.rs, Cargo.toml, Cargo.lock, README.md) |
| Dependencies | 5 direct (axum, serde, serde_json, sqlx, tokio) |
| Tests total | 3 |
| Tests effective | 3 (0 skipped) |
| Skip ratio | 0% |

## Findings

1. [high] R4 — GET /books/{id} unreachable under axum 0.7 route syntax
2. [high] R5 — PUT /books/{id} unreachable under axum 0.7 route syntax
3. [high] R6 — DELETE /books/{id} unreachable under axum 0.7 route syntax
4. [high] 2 of 3 tests fail (test_coverage=0.333) from the same route bug

All four share one root cause and one fix: use `/books/:id` (axum 0.7) or bump
axum to 0.8 in `Cargo.toml`.

## Reproduce

```bash
cd <run_dir>
cat scores.json                              # test_coverage=0.333, defect_rate=1.0
grep -A2 'name = "axum"' Cargo.lock          # 0.7.9
grep -A2 'name = "matchit"' Cargo.lock       # 0.7.3  -> {id} is literal
sed -n '118p' src/main.rs                     # .route("/books/{id}", ...)
```
