# Evaluation: language=python_model=sonnet_tooling=beads · rep 1

## Summary

- **Factors:** language=python, model=sonnet, tooling=beads
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 51 total / 0 skipped (51 effective) — `test_coverage=0.97` from retort.db (build+import+tests ran)
- **Build:** pass (Python import; `test_coverage=0.97` ⇒ modules imported and tests executed) — not re-run
- **Lint:** pass — `code_quality=0.667` from retort.db
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 1 medium, 2 low, 1 info)

Scores read from `retort.db` (the run's `completed` row, finished 2026-04-13): `test_coverage=0.97`, `code_quality=0.667`, `defect_rate=0.849`, `maintainability=0.614`, `idiomatic=0.76`, `requirement_coverage=1.0`. The archive's `scores.json` is a stale all-zero placeholder and was disregarded in favor of the DB row. Build/test/lint were **not** re-run per the skill's gate.

## Requirements

Checklist is the pinned `experiment-2/REQUIREMENTS.json` (12 items, constant denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing query tools | ✓ implemented | `server.py:11` `FastMCP(...)`; 16 `@app.tool()` handlers; `app.run(transport="stdio")` `server.py:644` |
| R2 | Loads provided datasets in data/kaggle/ | ✓ implemented | `data_loader.py:70-149` reads the 6 CSVs from `data/kaggle/`; `test_all_six_csv_files_queryable` |
| R3 | Match query by team (home/away/either) | ✓ implemented | `find_matches` `server.py:48`, `_filter_team` `server.py:31` |
| R4 | Filter by date range and/or season | ✓ implemented | `find_matches` `season`/`date_from`/`date_to` `server.py:85-92` |
| R5 | Filter by competition | ✓ implemented | `_filter_competition` `server.py:37`; comp tagged per loader (`data_loader.py:73,85,97`) |
| R6 | Team W/L/D record + goals for/against | ✓ implemented | `get_team_stats` `server.py:158`; `test_get_team_stats_returns_record` |
| R7 | Player search by name | ✓ implemented | `find_players` name filter `server.py:256`, `get_player_details` `server.py:290` |
| R8 | Filter players by nationality/club + ratings | ✓ implemented | `find_players` nationality/club/min_overall `server.py:258-266` |
| R9 | Season standings computed from matches | ✓ implemented | `get_league_standings` `server.py:355`; `test_get_league_standings_2019` (Flamengo champion) |
| R10 | Aggregate statistics | ✓ implemented | `get_competition_summary` `server.py:510`, `get_biggest_wins` `server.py:482`, `get_home_away_performance` `server.py:554` |
| R11 | Head-to-head records between two teams | ✓ implemented | `find_matches` H2H block `server.py:109-128`, `compare_teams` `server.py:215` |
| R12 | Automated tests covering query capabilities | ✓ implemented | `test_server.py` — 51 tests, 0 skips; `test_coverage=0.97` |

## Build & Test

Not re-run — stored scores used as the build+test signal (skill step 2).

```text
source: retort.db (run_results, status=completed, finished 2026-04-13 22:48)
test_coverage   = 0.97   # build/import OK + tests executed and passed
defect_rate     = 0.849
code_quality    = 0.667
maintainability = 0.614
idiomatic       = 0.76
requirement_coverage = 1.0
```

```text
skipped tests: 0  (grep pytest.skip / @pytest.mark.skip / xfail over *.py → 0)
test methods:  51 (grep 'def test_' test_server.py)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 1321 (server.py 644, data_loader.py 231, test_server.py 446) |
| Files (excl. __pycache__/data) | 14 (3 .py source) |
| Dependencies | pandas, mcp (imported; no manifest declares them) |
| Tests total | 51 |
| Tests effective | 51 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top items by severity (full list in `findings.jsonl`):

1. [medium] No dependency manifest (requirements.txt / pyproject.toml) — `server.py:6-7` imports pandas + mcp; nothing pins them.
2. [low] `BR-Football-Dataset.csv` loaded but excluded from combined match queries — `data_loader.py:199-227` omits `br_football` from `all_matches()`.
3. [low] Team filtering uses substring matching and can over-match — `server.py:31-34`.
4. [info] Tools return preformatted strings rather than structured data — all `@app.tool` handlers.

No critical/high findings: all 12 pinned requirements implemented, tests execute (test_coverage=0.97), zero skipped tests.

## Reproduce

```bash
cd experiment-2/runs/language=python_model=sonnet_tooling=beads/rep1
# scores (do not re-run toolchain):
db=../../../retort.db
sqlite3 -readonly "$db" "SELECT rr.metric_name, rr.value FROM run_results rr
  WHERE rr.run_id=(SELECT er.id FROM experiment_runs er
    WHERE json_extract(er.run_config_json,'\$.language')='python'
      AND json_extract(er.run_config_json,'\$.model')='sonnet'
      AND json_extract(er.run_config_json,'\$.tooling')='beads'
      AND er.replicate=1 AND er.status='completed'
    ORDER BY er.finished_at DESC LIMIT 1);"
# skip / test counts:
grep -rEn "pytest\.skip|@pytest\.mark\.skip|xfail" . --include="*.py" | wc -l
grep -rEc "def test_" test_server.py
# LOC:
wc -l server.py data_loader.py test_server.py
```
