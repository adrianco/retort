# Evaluation: effort=high language=python model=claude-opus-5-5 prompt=atdd-skill · rep 1

## Summary

- **Factors:** language=python, model=claude-opus-5-5, prompt=atdd-skill, effort=high
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Prompt conformance (atdd-skill):** 2/2 — four-layer ATDD structure present, all acceptance tests pass
- **Tests:** 120 passed / 0 failed / 0 skipped (120 effective) — final state in `_agent_stdout.log`
- **Build:** pass — `defect_rate=1.0` (scores.json); package builds, `python -m brazilian_soccer_mcp` runs
- **Lint/Quality:** `code_quality=0.667`, `maintainability=0.667`, `idiomatic=0.70` (scores.json)
- **Coverage:** `test_coverage=0.71` (scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 2 info)

Scores read from `{run_dir}/scores.json` (inline-gate run; no `retort.db` row yet). Not re-run.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing tools/handlers | ✓ implemented | `server.py:233` JSON-RPC 2.0 (`initialize`/`ping`/`tools/list`/`tools/call`), 16 tools in `TOOLS` |
| R2 | Loads/uses datasets in data/kaggle/ | ✓ implemented | `data.py:159` `_load` reads all 6 CSVs; `data/kaggle/` contains all 6 files |
| R3 | Match query by team (home/away/either) | ✓ implemented | `queries.py:253` `find_matches` + `select()` venue filter (`queries.py:214`) |
| R4 | Match filter by date range / season | ✓ implemented | `select()` `season`/`date_from`/`date_to` (`queries.py:226-232`) |
| R5 | Match filter by competition | ✓ implemented | `resolve_competition` (`queries.py:76`) spans Brasileirão/Copa/Libertadores |
| R6 | Team W/L/D record + goals for/against | ✓ implemented | `team_record` (`queries.py:305`), `Record`/`_tally` (`queries.py:135,165`) |
| R7 | Player search by name | ✓ implemented | `search_players`/`player_profile` (`queries.py:602,614`) |
| R8 | Player filter by nationality/club + ratings | ✓ implemented | `_player_filter` (`queries.py:572`); `player_dict` returns overall/potential |
| R9 | Season standings from match results | ✓ implemented | `standings` (`queries.py:346`) computes points/positions from matches |
| R10 | Aggregate statistics | ✓ implemented | `competition_stats`/`_summary` avg goals (`queries.py:481,667`), `biggest_wins`, `rank_teams` |
| R11 | Head-to-head between two teams | ✓ implemented | `head_to_head` (`queries.py:269`) returns W/L/D + goals |
| R12 | Automated tests exercising queries | ✓ implemented | 120 passed, 0 skipped; `test_coverage=0.71 > 0`, `defect_rate=1.0` |

**Prompt-factor instructions (`prompts/atdd-skill.md`):**

| ID | Instruction (short) | Status | Evidence |
|----|----|----|----|
| P1 | ATDD four-layer: spec → DSL → protocol driver → implementation | ✓ implemented | `tests/acceptance/` specs, `tests/acceptance/dsl/`, `tests/acceptance/drivers/mcp_driver.py` driving the real MCP interface |
| P2 | Work until every acceptance test passes | ✓ implemented | final `120 passed` in `_agent_stdout.log`; `defect_rate=1.0` |

No requirement is unimplemented, partial, or stubbed. Enhancements beyond spec (Série B/C,
derbies, knockout brackets, season comparison, combined team+player profile) are noted in
`findings.jsonl` as `info`, not deductions.

## Build & Test

Not re-run — stored mechanical scores used per skill policy.

```text
scores.json: {"code_quality": 0.667, "token_efficiency": 0.0107, "test_coverage": 0.71,
              "defect_rate": 1.0, "maintainability": 0.667, "idiomatic": 0.70}
```

```text
pytest (final, from _agent_stdout.log): 120 passed
skip scan: 0 (pytest.skip / @pytest.mark.skip / xfail)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 1,791 |
| Lines of code (tests) | 1,561 |
| Python files | 32 |
| Files (excl. data/artifacts) | 44 |
| Dependencies (runtime) | 0 (stdlib only; `pytest` test-only) |
| Tests total | 120 |
| Tests effective | 120 |
| Skip ratio | 0% |
| Coverage | 71% |

## Findings

Top items by severity (full list in `findings.jsonl`):

1. [low] queries.py is a single 691-line module (`qual-queries-size`)
2. [low] Line coverage is 71%, ~29% of paths unexercised (`cov-71`)
3. [info] Implements well beyond the spec — 16 tools, derbies, brackets (`enh-breadth`)
4. [info] MCP server is hand-rolled JSON-RPC 2.0 with zero runtime deps (`enh-stdlib-mcp`)

No critical/high/medium findings. This is a clean, spec-complete run that followed the
requested ATDD workflow.

## Reproduce

```bash
cd "experiments/adrianco/experiment-83-atdd-skill/smoke/runs/effort=high_language=python_model=claude-opus-5-5_prompt=atdd-skill/rep1"
cat scores.json                                   # stored mechanical scores (not re-run)
grep -aoE "===+ [0-9]+ passed[^=]*===+" _agent_stdout.log | tail -1   # final test state
ls data/kaggle/                                   # 6 provided CSVs
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" tests/ --include="*.py" | wc -l   # 0 skips
```
