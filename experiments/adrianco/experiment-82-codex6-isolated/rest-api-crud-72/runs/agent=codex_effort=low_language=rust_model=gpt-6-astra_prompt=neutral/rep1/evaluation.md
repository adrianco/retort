# Evaluation: rest-api-crud (agent=codex, effort=low, language=rust, model=gpt-6-astra, prompt=neutral) · rep 1

## Summary

- **Factors:** language=rust, model=gpt-6-astra, agent=codex, effort=low, prompt=neutral, framework=unknown (Axum in practice)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, R1–R12)
- **Tests:** 5 passed / 0 failed / 0 skipped (5 effective) — from `test_coverage=1.0`
- **Build:** pass — from `scores.json` (`test_coverage=1.0` ⇒ build + all tests passed); not re-run
- **Lint:** pass — `code_quality=0.83` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 4 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `lib.rs:139 create`, INSERT at `lib.rs:145-148` |
| R2 | GET /books lists all books | ✓ implemented | `lib.rs:163 list`, SELECT `lib.rs:171` |
| R3 | GET /books ?author= filter | ✓ implemented | `lib.rs:159-162 Filter`, `WHERE (?1 IS NULL OR author = ?1)` `lib.rs:171`; test `tests.rs:74` |
| R4 | GET /books/{id} single (404 if absent) | ✓ implemented | `lib.rs:176 fetch` → `select` `lib.rs:129-138` returns `not_found()` |
| R5 | PUT /books/{id} updates | ✓ implemented | `lib.rs:183 update`, UPDATE `lib.rs:191-194`, 404 when 0 rows |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `lib.rs:202 delete`, DELETE `lib.rs:208`, 404 when 0 rows |
| R7 | Data stored in SQLite/embedded | ✓ implemented | `rusqlite` bundled (`Cargo.toml:8`), table DDL `lib.rs:101-109`; persistence test `tests.rs:171` |
| R8 | JSON responses + correct status codes | ✓ implemented | 201 `lib.rs:153`, 200, 404 `lib.rs:72`, 400 `lib.rs:42`, 405 `lib.rs:115-116`; JSON errors `lib.rs:53` |
| R9 | Validation: title & author required | ✓ implemented | `BookInput::validate` `lib.rs:37-47`; `deny_unknown_fields` `lib.rs:28`; SQL CHECK `lib.rs:104-105`; test `tests.rs:110` |
| R10 | GET /health | ✓ implemented | `lib.rs:111` returns `{"status":"ok"}`; test `tests.rs:144` |
| R11 | README with setup/run | ✓ implemented | `README.md` — build/test/run, env vars, API table, curl examples |
| R12 | ≥3 unit/integration tests | ✓ implemented | 5 `#[tokio::test]` in `tests.rs`; `test_coverage=1.0` |

No requirements missing or partial. Enhancements beyond spec: SQL-injection-safe parameterized filter (tested), defense-in-depth validation (app + DB CHECK), blocking-pool DB dispatch, graceful shutdown, `Location` header on create.

## Build & Test

Build/test not re-run per skill guidance — stored mechanical scores are authoritative:

```text
scores.json
test_coverage = 1.0   ⇒ cargo build + cargo test succeeded, all tests passed
defect_rate   = 1.0   ⇒ build+test succeeded
code_quality  = 0.833 ⇒ lint/quality signal
idiomatic     = 0.78
maintainability = 0.478
```

```text
grep #[test]/#[tokio::test] tests.rs  → 5 tests
grep #[ignore] *.rs                   → 0 skipped/ignored
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 431 (lib.rs 217, tests.rs 196, main.rs 18) |
| Files (source) | 3 (.rs) |
| Dependencies | 5 runtime (axum, rusqlite, serde, serde_json, tokio) + 2 dev |
| Tests total | 5 |
| Tests effective | 5 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (all info; full list in `findings.jsonl`):

1. [info] E1 — Parameterized author filter is SQL-injection safe and tested
2. [info] E2 — Defense-in-depth validation (app trim/non-blank + table CHECK)
3. [info] E3 — SQLite dispatched to blocking pool; file-persistence tested across reopen
4. [info] N1 — Author filter is exact/case-sensitive match (spec-compliant; cross-run note)

## Reproduce

```bash
cd "experiments/adrianco/experiment-82-codex6-isolated/rest-api-crud-72/runs/agent=codex_effort=low_language=rust_model=gpt-6-astra_prompt=neutral/rep1"
cat scores.json                                   # authoritative build/test/lint scores
cat ../../REQUIREMENTS.json                        # pinned R1–R12 checklist
grep -rE "#\[(tokio::)?test\]" . --include="*.rs" | wc -l   # 5 tests
grep -rE "#\[ignore\]" . --include="*.rs" | wc -l           # 0 skips
# (build/test intentionally NOT re-run — test_coverage=1.0 already recorded)
```
