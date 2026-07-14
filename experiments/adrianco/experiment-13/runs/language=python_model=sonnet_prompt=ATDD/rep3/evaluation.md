# Evaluation: language=python_model=sonnet_prompt=ATDD · rep 3

## Summary

- **Factors:** language=python, model=sonnet, prompt=ATDD
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, R1–R12)
- **Prompt conformance (ATDD):** followed — executable acceptance tests through the public MCP interface, unit TDD underneath. One literal deviation (P4, see Findings).
- **Tests:** 46 collected (14 acceptance + 32 unit) / 0 failed / 0 skipped (46 effective) — `test_coverage=1.0`
- **Build:** pass — from `scores.json` `test_coverage=1.0` (build + tests executed; not re-run)
- **Lint:** pass — `code_quality=0.667` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 6 items in `findings.jsonl` (0 critical, 0 high, 3 medium, 2 low, 1 info)

Stored mechanical scores (`scores.json`): test_coverage=1.0, code_quality=0.667, defect_rate=0.963,
maintainability=0.631, idiomatic=0.76, token_efficiency=0.009.

## Requirements

Checklist is the pinned `experiment-13/REQUIREMENTS.json` (constant denominator = 12).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing query tools | ✓ implemented | `server.py:18` FastMCP + 6 `@mcp.tool()` handlers |
| R2 | Loads provided `data/kaggle/` datasets | ✓ implemented | `data_loader.py:112-194` reads all 6 CSVs |
| R3 | Match query by team (home/away/either) | ✓ implemented | `server.py:81` `find_matches(team=)` via `_team_filter`; tests 2,12 |
| R4 | Match query by date range / season | ✓ implemented | `server.py:100-107` `season`/`date_from`/`date_to`; test 2 |
| R5 | Match query by competition | ✓ implemented | `server.py:96-98`; tests 8,11 |
| R6 | Team W/L/D record + goals for/against | ✓ implemented | `server.py:125` `get_team_stats`; test 3 (Flamengo 2019 = 90 pts) |
| R7 | Player search by name | ✓ implemented | `server.py:236-237` `find_players(name=)` |
| R8 | Players by nationality/club + ratings | ✓ implemented | `server.py:239-249`; tests 4,5,14 |
| R9 | Season standings computed from matches | ✓ implemented | `server.py:360` `get_standings`; test 7 (Flamengo champion, 90 pts) |
| R10 | Aggregate statistics | ✓ implemented | `server.py:459` `get_statistics` (4 stat types); tests 9,13 |
| R11 | Head-to-head between two teams | ✓ implemented | `server.py:279` `get_head_to_head`; test 6 |
| R12 | Automated tests covering query capabilities | ✓ implemented | 46 tests, `test_coverage=1.0` |

### Prompt-factor instructions (ATDD)

| ID | Instruction (short) | Status | Evidence |
|----|----|----|----|
| P1 | Translate each requirement into an executable acceptance test | ✓ implemented | `tests/test_acceptance.py` — 14 scenario tests across all tools |
| P2 | Exercise SUT only through public interface, no back-door internals | ✓ implemented | tests use `create_connected_server_and_client_session` + `session.call_tool` (MCP protocol); no import of query internals |
| P3 | Assert WHAT not HOW, in domain language | ✓ implemented | asserts on matches/standings/head-to-head outcomes |
| P5 | Finer-grained unit TDD underneath | ✓ implemented | `tests/test_unit.py` — 32 unit tests on `DataLoader`/helpers |
| P4 | Each scenario starts from a running but *empty* system, shares no data | ~ partial | tests assert on full real dataset values; data is module-global, loaded at import (`server.py:19-20`) — see findings |
| P6 | Tests fail first, then implemented to green | cannot-verify | final archive only; no red→green history available |

## Build & Test

Not re-run — stored scores used (per skill step 2).

```text
source: scores.json
test_coverage = 1.0   => build succeeded AND all tests passed (test gate)
defect_rate   = 0.963 => build+test success
```

```text
tests collected: 46  (tests/test_acceptance.py: 14, tests/test_unit.py: 32)
failed: 0   skipped: 0   effective: 46
skip scan: grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" tests/  ->  0 matches
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source: server.py + data_loader.py) | 744 |
| Lines of code (tests) | 603 |
| Python files | 5 |
| Dependencies declared | 0 (no manifest — mcp + pandas imported, undeclared) |
| Tests total | 46 |
| Tests effective | 46 |
| Skip ratio | 0% |
| Build | pass (test_coverage=1.0) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [medium] P4 — ATDD prompt asks each scenario to start from an empty system sharing no data; tests instead assert on full real dataset values held in module-global state.
2. [medium] R11/R10 — head-to-head and statistics query the un-deduplicated `get_all_matches()` union; BR-Football "Serie A"/"Copa do Brasil" rows overlap the dedicated CSVs and can double-count.
3. [medium] No dependency manifest (requirements.txt/pyproject) declaring `mcp` and `pandas`.
4. [low] `get_standings` builds a league points table even for knockout competitions (Copa do Brasil, Libertadores).
5. [low] Date-range filtering compares against possibly-empty `''` date strings produced by unparseable dates.

(Plus 1 info: build + 46 tests pass, 0 skips.)

## Reproduce

```bash
cd "experiment-13/runs/language=python_model=sonnet_prompt=ATDD/rep3"
# Mechanical scores (build/test/lint) read from the archive — not re-run:
cat scores.json
# Skip scan:
grep -rEn "pytest\.skip|@pytest\.mark\.skip|xfail" tests/ --include="*.py"
# Test inventory:
grep -cE "^def test_" tests/test_acceptance.py     # 14
grep -cE "def test_"  tests/test_unit.py            # 32
# (Fallback only, if scores.json were absent:)  python -m pytest tests/ -q
```
