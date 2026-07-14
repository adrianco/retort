# Evaluation: language=python · model=opus · tooling=beads · rep 1

## Summary

- **Factors:** language=python, model=opus, tooling=beads
- **Status:** ok — original run passed; see caveat on archival below
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (`requirement_coverage=1.0` from retort.db)
- **Tests:** 24 total, 0 skipped. Authoritative `test_coverage=0.85` (retort.db, scored 2026-04-13). In the **archived** workspace 6 pass / 18 fail because `data/kaggle/` is not bundled.
- **Build:** pass — `defect_rate=0.68` from retort.db (build + most tests succeeded with data present)
- **Lint:** pass — `code_quality=0.667`, `maintainability=0.617`, `idiomatic=0.68` (retort.db)
- **Architecture:** `run-summary` skill not available in this session; brief overview inline below
- **Findings:** 4 items in `findings.jsonl` (0 critical, 1 high, 2 low, 1 info)

> **Score-source note.** This run has two scoring snapshots. The retort.db `completed` row
> (finished 2026-04-13, data present) is authoritative: `test_coverage=0.85`,
> `defect_rate=0.68`, `requirement_coverage=1.0`, `code_quality=0.667`. The archive's
> `scores.json` (written 2026-06-12 09:27) shows `test_coverage=0.3` / `defect_rate=0.0`
> — a **degraded local re-score** produced because `data/kaggle/` is absent from the
> archived workspace, so the 18 data-dependent tests error out. Evaluation uses the
> authoritative DB scores and flags the archival gap as a finding.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing tools/handlers | ✓ implemented | `soccer_mcp/server.py:175` `build_server` uses `mcp.server.Server`, `@list_tools`/`@call_tool`; 9 `TOOL_DEFS`; `main()` entrypoint + `[project.scripts]` |
| R2 | Loads provided data/kaggle CSVs | ✓ implemented | `data_loader.py:146` `load_all` reads all 6 CSVs (Brasileirão, Cup, Libertadores, BR-Football, histórico, FIFA) |
| R3 | Match query by team (home/away/either) | ✓ implemented | `query.py:33` `find_matches` + `_team_mask` with `side=home/away/either` |
| R4 | Filter by date range and/or season | ✓ implemented | `query.py:44-49` `season`, `date_from`, `date_to` filters |
| R5 | Filter by competition | ✓ implemented | `query.py:42` competition substring filter over unified frame spanning all 3 competitions |
| R6 | Team W/L/D record + goals for/against | ✓ implemented | `query.py:77` `team_record` returns wins/draws/losses, goals_for/against, points |
| R7 | Player search by name | ✓ implemented | `query.py:164` `find_players(name=...)` over FIFA data |
| R8 | Player filter by nationality/club + ratings | ✓ implemented | `query.py:166-176` nationality/club/position/min_overall; returns Overall/Potential |
| R9 | Season standings computed from matches | ✓ implemented | `query.py:120` `standings` builds points table from results (3/1/0) |
| R10 | Aggregate statistics | ✓ implemented | `query.py:179` `biggest_wins`, `query.py:188` `average_goals` (avg goals, home win rate) |
| R11 | Head-to-head between two teams | ✓ implemented | `query.py:52` `head_to_head` returns wins_a/wins_b/draws + sample |
| R12 | Automated tests covering capabilities | ✓ implemented | 24 tests in `tests/test_*.py`; `test_coverage=0.85` (>0) in retort.db. *Not re-runnable in archive — see `data-missing` finding.* |

No requirements are missing or stubbed. `requirement_coverage=1.0` in retort.db corroborates 12/12.

## Build & Test

Build/test were **not re-run** (per skill — stored scores reused). Authoritative scores from `retort.db` (completed row, finished 2026-04-13):

```text
test_coverage    = 0.85   (tests executed, ~85% coverage with data present)
defect_rate      = 0.68   (build + tests largely succeeded)
requirement_cov  = 1.00
code_quality     = 0.667
maintainability  = 0.617
idiomatic        = 0.68
```

Archived-workspace re-score (`scores.json`, degraded — `data/kaggle/` absent):

```text
test_coverage = 0.3   defect_rate = 0.0
# .pytest_cache/v/cache/lastfailed: 18 failing tests — all engine/datasets-fixture
# tests (conftest.py load_all() -> FileNotFoundError on missing CSVs).
# 6 data-free tests still pass: 5 normalization tests + test_all_tools_have_schema.
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 630 (`soccer_mcp/*.py`) |
| Lines of test code | 186 (`tests/*.py`) |
| Python files | 10 |
| Dependencies | 2 (pandas, mcp) |
| Tests total | 24 |
| Tests effective | 24 (0 skipped) |
| Skip ratio | 0% |
| MCP tools exposed | 9 |

## Findings

Top items by severity (full list in `findings.jsonl`):

1. [high] `data-missing` — Archived workspace omits `data/kaggle/`, so 18/24 tests fail on re-score; `scores.json` is degraded vs authoritative DB scores.
2. [low] `R12` — Comprehensive test suite is not runnable in the archived workspace (data fixtures not shipped).
3. [low] `deadcode-normalize` — Dead partial-match loop in `data_loader.py:66-70` (`pass` in every branch).
4. [info] `bdd-style` — Tests use plain pytest with `Scenario:` docstrings rather than gherkin BDD suggested by TASK.md.

## Reproduce

```bash
cd experiment-2/runs/language=python_model=opus_tooling=beads/rep1
# Authoritative scores (do NOT re-run toolchain):
sqlite3 -readonly ../../../retort.db "
  SELECT rr.metric_name, rr.value FROM run_results rr
  WHERE rr.run_id=(SELECT er.id FROM experiment_runs er
    WHERE json_extract(er.run_config_json,'\$.language')='python'
      AND json_extract(er.run_config_json,'\$.model')='opus'
      AND json_extract(er.run_config_json,'\$.tooling')='beads'
      AND er.replicate=1 AND er.status='completed'
    ORDER BY er.finished_at DESC LIMIT 1);"
# Degraded re-score source:
cat scores.json
cat .pytest_cache/v/cache/lastfailed   # 18 data-dependent failures
# Metrics:
wc -l soccer_mcp/*.py tests/*.py
```
