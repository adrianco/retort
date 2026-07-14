# Evaluation: language=python · model=sonnet · prompt=ATDD · rep 1

## Summary

- **Factors:** language=python, model=sonnet, prompt=ATDD
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, 12 items)
- **Prompt conformance (ATDD):** substantially followed — acceptance tests drive through the public MCP interface; one minor deviation (P3, see findings)
- **Tests:** 83 passed / 0 failed / 0 skipped (83 effective) — `test_coverage=1.0` from `scores.json`
- **Build:** pass (test_coverage=1.0 ⇒ build + all tests executed; not re-run per skill)
- **Lint:** pass — `code_quality=0.667`, `idiomatic=0.58` from `scores.json`
- **Architecture:** run-summary skill unavailable in this environment (no `summary/`)
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 2 info)

## Requirements

Denominator is the pinned 12-item `experiment-13/REQUIREMENTS.json`.

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing query tools | ✓ implemented | `server.py:24` `build_server`, `@app.list_tools`/`@app.call_tool`, 5 tools registered |
| R2 | Load provided datasets in data/kaggle/ | ✓ implemented | `data_loader.py:39-111` reads all 6 CSVs; `data/kaggle/` has all files |
| R3 | Match query by team (home/away/either) | ✓ implemented | `data_loader.py:198-201` OR mask on home/away; `test_acceptance.py:97` |
| R4 | Match query by date range / season | ✓ implemented | `data_loader.py:208-215`; `test_acceptance.py:134,153` |
| R5 | Match query by competition (3 comps) | ✓ implemented | `data_loader.py:140-180` `_competition_df`; `test_acceptance.py:116-132` |
| R6 | Team W/L/D record + goals for/against | ✓ implemented | `data_loader.py:234-285` `get_team_stats`; `test_acceptance.py:182` |
| R7 | Player search by name | ✓ implemented | `data_loader.py:298-299`; `test_acceptance.py:234` |
| R8 | Player filter by nationality/club + ratings | ✓ implemented | `data_loader.py:300-322`; `test_acceptance.py:217,227,247` |
| R9 | Standings computed from match results | ✓ implemented | `data_loader.py:326-384` `get_standings` (3pt/win); `test_acceptance.py:280` |
| R10 | Aggregate stats (avg goals, biggest wins, home record) | ✓ implemented | `data_loader.py:386-449` `get_statistics`; `test_acceptance.py:310-349` |
| R11 | Head-to-head between two teams | ✓ implemented | `find_matches` `opponent` param `data_loader.py:203-206`; `test_acceptance.py:106` |
| R12 | Automated tests covering query capabilities | ✓ implemented | 83 tests (39 acceptance + 44 unit), 0 skips, `test_coverage=1.0` |

### ATDD prompt instructions

| ID | Instruction (short) | Status | Evidence |
|----|----|----|----|
| P1 | Acceptance tests exercise SUT only via public MCP interface, no back-door | ✓ implemented | `test_acceptance.py:14,40` uses `create_connected_server_and_client_session`; calls go through `session.call_tool` |
| P2 | Assert WHAT not HOW, in domain language | ✓ implemented | tests assert on matches/standings/players, not internals (e.g. `test_win_draw_loss_sum_equals_total_matches`) |
| P3 | Atomic, independent scenarios from an empty system, no shared data | ~ partial | fresh server per test (`test_acceptance.py:21` fixture); but backed by full shipped dataset, asserting dataset-specific facts rather than a seeded empty system |

## Build & Test

Per the evaluate-run skill, build/test/lint were **not re-run** — stored scores are authoritative.

```text
scores.json
test_coverage = 1.0   → build succeeded + all 83 tests executed and passed
defect_rate   = 1.0   → build+test succeeded
code_quality  = 0.667 (ruff-based)
idiomatic     = 0.58
maintainability = 0.655
```

```text
Tests collected (static): 83
  tests/test_acceptance.py — 39 (MCP-protocol acceptance, in-process client session)
  tests/test_unit.py       — 44 (DataLoader unit TDD underneath)
Skips/xfail: 0
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source: server.py + data_loader.py) | 614 |
| Lines of code (tests) | 616 |
| Files (excl. artifacts/data) | 15 |
| Dependencies (requirements.txt) | 5 |
| Tests total | 83 |
| Tests effective (passed+failed) | 83 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Full list in `findings.jsonl` (4 items). Top by severity:

1. [low] P3 — ATDD prompt asks scenarios to start from an empty system; acceptance tests run against the full shipped dataset
2. [low] Team matching uses substring `contains`, which can over-match merged clubs (e.g. "Atletico")
3. [info] run-summary skill unavailable — no architecture map generated
4. [info] code_quality moderate (0.667) / idiomatic (0.58) — style only, no correctness impact

No critical, high, or medium findings. This is a clean, conformant run: all 12 spec requirements implemented, the ATDD prompt's core asks (public-interface acceptance tests driving the work) are met, and the full test suite executes with zero skips.

## Reproduce

```bash
cd experiment-13/runs/language=python_model=sonnet_prompt=ATDD/rep1
# Scores are authoritative (do not re-run); to reproduce locally:
pip install -r requirements.txt
python -m pytest            # 83 passed
# Static checks already captured in scores.json (test_coverage=1.0, code_quality=0.667)
```
