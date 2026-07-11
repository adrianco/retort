# Evaluation: agent=hermes-local_language=rust_prompt=neutral · rep 1

## Summary

- **Factors:** language=rust, agent=hermes-local (Qwen3-Coder-Next), prompt=neutral, framework=unknown
- **Status:** ok (all requirements met and tests pass) — **but with a CRITICAL archiving defect: the archived `run_dir` contains no source code.** The scored code exists only in a self-repair clone temp workspace.
- **Requirements:** 12/12 implemented, 0 partial, 0 missing *(assessed against the scored self-repair code)*
- **Tests:** 8 passed / 0 failed / 0 skipped (8 effective) — `test_coverage=1.0` from scores.json
- **Build:** pass — `test_coverage=1.0` ⇒ build + all tests passed (not re-run)
- **Lint:** pass — `code_quality=0.833` from scores.json
- **Architecture:** summary skill not invoked (no source in archive to summarize; see note below)
- **Findings:** 5 items in `findings.jsonl` (1 critical, 1 high, 1 low, 2 info)

## ⚠️ Important: what actually got scored

The archived run directory is **not self-contained**. It holds only `TASK.md`, `stack.json`,
`scores.json`, and agent logs — no `Cargo.toml`, no `src/`, no `tests/`, no `README.md`.

Reconstructing what happened from the logs, git state, and surviving temp workspaces:

1. **First attempt** (`.../retort-local-76rb7tam/retort-d88eeb957eb5`) produced **zero source
   files**. The local hermes write-guard refused every `write_file` under `/private/var/folders/...`
   as a "sensitive system path" (`_agent_stdout.log`). `git` shows *"No commits yet"*;
   `.hermes_usage.json` has `completed=false`. This empty workspace is what got archived as rep1.
2. **Self-repair clone** (`.../retort-0f2422d0999c`, contains `FEEDBACK.md`) then wrote a
   complete Actix-web + SQLx/SQLite implementation and **all 8 tests pass**. `scores.json`
   (mtime matches this clone) reflects *this* code — `test_coverage=1.0`, `defect_rate=0.922`
   (the sub-1.0 defect_rate is consistent with the half-credit self-repair rule).

So the scores are legitimate, but they describe code that was **not preserved in the archive**.
This evaluation assesses the scored self-repair code; all file:line evidence below points at
`retort-0f2422d0999c` because that is the only place the deliverable exists.

## Requirements

Assessed against the scored self-repair workspace `retort-0f2422d0999c`.

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `src/routes.rs:33 create_book` → `src/db.rs:81 INSERT ... RETURNING` |
| R2 | GET /books lists all books | ✓ implemented | `src/routes.rs:20 list_books` → `src/db.rs:34 get_all_books` |
| R3 | GET /books ?author= filter | ✓ implemented | `src/routes.rs:16 ListBooksQuery.author`; `src/db.rs:43 WHERE author = ?`; `tests:234 test_author_filter` |
| R4 | GET /books/{id} (404 if absent) | ✓ implemented | `src/routes.rs:53 get_book`; `tests:217 test_get_nonexistent_book` → 404 |
| R5 | PUT /books/{id} updates | ✓ implemented | `src/routes.rs:67 update_book` → `src/db.rs:102` COALESCE update; `tests:103 test_update_book` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `src/routes.rs:82 delete_book`; `tests:147 test_delete_book` → 204 |
| R7 | Stored in SQLite | ✓ implemented | `src/db.rs:2 sqlx sqlite`, `create_pool` → `database.db`; CREATE TABLE books |
| R8 | JSON + correct status codes | ✓ implemented | 201/200/404/400/204 across `src/routes.rs`; `src/models.rs:42 ResponseError` |
| R9 | Validation: title & author required | ✓ implemented | `src/routes.rs:38-43` empty-string → 400; `tests:183 test_validation_errors` (see low finding: whitespace-only slips through) |
| R10 | GET /health | ✓ implemented | `src/routes.rs:8 health_check`; `tests:8 test_health_check` |
| R11 | README with setup/run | ✓ implemented | `README.md` — build/run/test + DATABASE_URL docs |
| R12 | ≥3 tests | ✓ implemented | 8 `#[actix_web::test]` fns, all pass (`test_coverage=1.0`) |

## Build & Test

Not re-run — stored scores used per skill (compiled-language re-run is the slow path):

```text
test_coverage = 1.0    ⇒ cargo build + cargo test succeeded, all 8 tests pass
code_quality  = 0.833  ⇒ lint/quality (Lint: pass)
defect_rate   = 0.922  ⇒ build+test succeeded; sub-1.0 consistent with self-repair half-credit
```

Agent's own report (`retort-0f2422d0999c/_agent_stdout.log`): "All 8 tests pass" — health,
validation, 404, get-by-id, delete, author-filter, create/list, update.

## Metrics

Computed on the scored self-repair workspace (archive has no source to measure).

| Metric | Value |
|--------|-------|
| Lines of code (source only, src/ + tests/) | 606 |
| Files (excl. target/.git) | 17 |
| Dependencies (Cargo.toml) | 5 (actix-web, serde, serde_json, sqlx, tokio; +thiserror) |
| Tests total | 8 |
| Tests effective | 8 |
| Skip ratio | 0% |
| Build/test | pass (test_coverage=1.0) |
| Token efficiency | 0.108 (90 api calls, 4.5M total tokens) |

## Findings

Top items by severity (full list in `findings.jsonl`):

1. **[critical] archive-empty** — Archived `run_dir` contains no source code; the deliverable
   (Cargo.toml, src/, tests/, README) exists only in the self-repair temp clone
   `retort-0f2422d0999c` and is unreproducible once temp is cleaned. Archiver kept the empty
   first-attempt workspace instead of the winning clone.
2. **[high] sandbox-write-guard** — First attempt wrote zero files; the local hermes write-guard
   refused all writes under `/private/var/folders/...` as a "sensitive system path". Run only
   passed via the self-repair clone. Root cause shared with the critical finding.
3. **[low] R9-validation-weak** — Required-field check uses `is_empty()` only; whitespace-only
   title/author passes; absent fields rejected only incidentally by serde.
4. **[info] extra-tests** — 8 integration tests, exceeding the "at least 3" requirement.
5. **[info] token-efficiency-low** — 0.108, inflated by the failed first attempt + repair round.

## Reproduce

```bash
run_dir="experiment-22-qwennext80b/bookshop/runs/agent=hermes-local_language=rust_prompt=neutral/rep1"

# The archive is NOT self-contained — confirm no source is present:
find "$run_dir" -type f -not -path '*/target/*'          # only TASK/stack/scores/logs

# Stored scores (do not re-run the toolchain):
cat "$run_dir/scores.json"

# The scored code lives in the surviving self-repair clone (temp — volatile):
D=/private/var/folders/n4/bm2w6rts32v24w3lbbm8yj8r0000gn/T/retort-local-76rb7tam/retort-0f2422d0999c
find "$D" -type f -not -path '*/target/*' -not -path '*/.git/*'
grep -rcE 'async fn test_' "$D/tests/integration_tests.rs"   # 8
```

*Note:* the `run-summary` skill was not invoked — the archive has no source tree to analyze, and
the scored code sits in a volatile temp directory. If the archiver is fixed to preserve the
self-repair workspace, re-run this evaluation to generate `summary/`.
