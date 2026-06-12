# Evaluation: language=python_model=opus-4.8-fast_prompt=ATDD · rep 1

## Summary

- **Factors:** language=python, model=opus-4.8-fast, prompt=ATDD
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, R1–R12) · ATDD prompt instructions P1–P5: 4 implemented, 1 cannot-verify (red-first ordering not observable from final artifact)
- **Tests:** all pass / 0 failed / 0 skipped (test_coverage=0.97, defect_rate=1.0 from scores.json) — 34 test functions (47 effective with parametrization)
- **Build:** pass (derived from test_coverage=0.97 — tests executed ⇒ package importable/built)
- **Lint:** code_quality=0.667 (scorer-computed; from scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

Source: pinned `experiment-13/REQUIREMENTS.json` (constant denominator, 12 items).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing query tools | ✓ implemented | `server.py:36` FastMCP + 6 `@mcp.tool()`; `test_acceptance.py:54` advertises capabilities |
| R2 | Loads provided data/kaggle CSVs | ✓ implemented | `loader.py:246` `load_matches`, reads 6 CSVs; `test_real_data.py:41` loads real data |
| R3 | Match query by team (home/away/either) | ✓ implemented | `knowledge_base.py:59` `find_matches` + `_involves`; `test_acceptance.py:95` |
| R4 | Filter by date range / season | ✓ implemented | `knowledge_base.py:75,86-89`; `test_acceptance.py:105,135` |
| R5 | Filter by competition (Brasileirão/Copa/Liberta.) | ✓ implemented | `knowledge_base.py:43-47`; `test_acceptance.py:119`, cross-file `:315` |
| R6 | Team record W/L/D + goals for/against | ✓ implemented | `knowledge_base.py:95` `team_record`; `test_acceptance.py:165` |
| R7 | Player search by name | ✓ implemented | `knowledge_base.py:174` `search_players` name filter; `test_acceptance.py:224` |
| R8 | Player filter by nationality/club + ratings | ✓ implemented | `knowledge_base.py:191-200`; `test_acceptance.py:234,244,253` |
| R9 | Season standings computed from matches | ✓ implemented | `knowledge_base.py:204` `standings` (3/1/0 pts); `test_acceptance.py:266` |
| R10 | Aggregate stats (avg goals, home/away, biggest) | ✓ implemented | `knowledge_base.py:252` `competition_stats`; `test_acceptance.py:288,301` |
| R11 | Head-to-head between two teams | ✓ implemented | `knowledge_base.py:138` `head_to_head`; `test_acceptance.py:194` |
| R12 | Automated tests for query capabilities | ✓ implemented | 3 test files, 34 functions; test_coverage=0.97 > 0 |

### Prompt-factor instructions (ATDD)

| ID | Instruction (short) | Status | Evidence |
|----|----|----|----|
| P1 | Each requirement → executable acceptance test | ✓ implemented | `test_acceptance.py` one scenario per capability category (match/team/player/standings/stats) |
| P2 | Drive SUT only through public MCP interface, no back-door | ✓ implemented | `conftest.py:135-148` real in-memory MCP session; `call()` only via `session.call_tool` |
| P3 | Assert WHAT not HOW, domain language | ✓ implemented | Domain-named scenarios + result-shape asserts (`test_acceptance.py:70,266`) |
| P4 | Atomic/independent, each from empty system | ✓ implemented | `conftest.py:116` per-test `tmp_path` dataset; fresh server per call |
| P5 | Tests fail first, then unit-TDD underneath | ~ cannot-verify (red-first) | Unit layer present (`test_unit.py`); initial red state not observable from archived final artifact |

## Build & Test

Per the skill, mechanical scores were read from `scores.json` (not re-run):

```text
scores.json
  test_coverage     = 0.97   # tests executed; build/import OK; 97% line coverage
  defect_rate       = 1.0    # build + tests succeeded
  code_quality      = 0.667  # lint/quality
  maintainability   = 0.288
  idiomatic         = 0.68
  token_efficiency  = 1.0
```

Skip scan (Step 5):

```text
grep -rE "pytest.skip|@pytest.mark.skip|skipif|xfail" tests/
  tests/test_real_data.py:26  skipif(not DATA_DIR.exists())   # guard did NOT fire — data present
```

No unconditional skips, no xfail. effective_tests = passed (0 skipped).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source + tests) | 1634 |
| Python files (source + tests) | 10 |
| Dependencies | 3 (mcp, pytest, pytest-asyncio) |
| Test functions | 34 (acceptance 21, unit 7, real-data 6) |
| Test functions effective (with parametrize) | ~47 |
| Skip ratio | 0% (1 conditional skipif, did not fire) |
| Line coverage | 97% |

## Findings

Full list in `findings.jsonl` (none at medium or above):

1. [low] Lint/quality score below ceiling — `scores.json` code_quality=0.667
2. [info] Real-data suite conditionally skipped when `data/kaggle` absent (guard did not fire) — `tests/test_real_data.py:24-27`
3. [info] Query surface exceeds minimal spec (home_away, min_overall, draw_rate, biggest_wins) — `knowledge_base.py`

## Reproduce

```bash
cd experiment-13/runs/language=python_model=opus-4.8-fast_prompt=ATDD/rep1
cat scores.json                                              # stored mechanical scores
grep -rE "pytest.skip|skipif|xfail" tests/ --include="*.py"  # skip scan
# Optional re-run of the suite (not required — scores already stored):
#   python -m pytest -q
```
