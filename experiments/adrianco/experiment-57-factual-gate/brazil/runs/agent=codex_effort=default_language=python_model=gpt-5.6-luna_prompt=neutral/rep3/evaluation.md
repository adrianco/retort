# Evaluation: agent=codex model=gpt-5.6-luna prompt=neutral · rep 3

## Summary

- **Factors:** language=python, agent=codex, model=gpt-5.6-luna, prompt=neutral, effort=default
- **Status:** ok — spec-complete, all tests pass
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 10 passed / 0 failed / 0 skipped (10 effective) — `defect_rate=1.0`, `test_coverage=0.92` (line coverage) from `scores.json`
- **Build:** pass — stdlib only, no deps (`test_coverage=0.92 ⇒ imports + tests ran`)
- **Lint:** n/a — `code_quality=0.833`, `idiomatic=0.75`, `maintainability=0.256` from `scores.json`
- **Factual gate:** `factual_accuracy=0.5` — Flamengo record assertion **passed**; "all 20 clubs" assertion **failed as a gate artifact** (see below), not a real defect
- **Architecture:** single-module design (`soccer_mcp.py`); run-summary skill not available, summarised inline
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 3 low)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing tools/handlers | ✓ implemented | `soccer_mcp.py:246 _mcp_result`, `TOOLS` (7), `main()` stdio JSON-RPC |
| R2 | Load & use datasets in data/kaggle/ | ✓ implemented | `soccer_mcp.py:103-123` loads 6 CSVs; 23,954 matches, 18k+ players |
| R3 | Match query by team (home/away/either) | ✓ implemented | `search_matches` team param matches home OR away (`:149`) |
| R4 | Filter by date range and/or season | ✓ implemented | `search_matches` start_date/end_date/season (`:139-168`) |
| R5 | Filter by competition (Brasileirão, Copa, Libertadores) | ✓ implemented | competitions loaded (`:104-108`) + filter (`:160-167`) |
| R6 | Team W/L/D record + goals for/against | ✓ implemented | `team_stats` (`:173-182`) |
| R7 | Player search by name | ✓ implemented | `search_players` name (`:192-196`) |
| R8 | Filter players by nationality/club + ratings | ✓ implemented | nationality/club/min_overall, Overall returned (`:192-196`) |
| R9 | Standings computed from match results | ✓ implemented | `standings` (`:198-206`) aggregates points/GD live |
| R10 | Aggregate statistics | ✓ implemented | `statistics` avg goals, home/away wins (`:225-228`) |
| R11 | Head-to-head between two teams | ✓ implemented | `head_to_head` (`:184-190`) |
| R12 | Automated tests covering queries | ✓ implemented | `test_soccer_mcp.py` 10 tests, 0 skips, `defect_rate=1.0` |

## Build & Test

Scores read from `scores.json` (inline gate) — toolchain not re-run per skill guidance.

```text
test_coverage = 0.92   # imports + tests executed (line coverage)
defect_rate   = 1.0    # build + all tests passed
10 test functions, 0 skips (grep pytest.skip/unittest.skip/xfail = 0)
```

### Factual gate (the point of experiment-57)

```text
_factual.json → ok=false, score=0.5
  ✓ "2019 Série A: Flamengo's record" — expected 28W-6D-4L, got 28W-6D-4L
  ✗ "2019 Série A: all 20 clubs present" — expected 20/20, got 19/20
      (1 Atlético/Athletico row(s), expected 2)
```

**This failure is a gate measurement artifact, not an implementation defect.** Verified two ways:
- `standings(2019)` returns 20 distinct rows including **both** `Atletico-MG` and `Atletico-PR`.
- `test_atletico_variants_remain_distinct` passes: each Atlético has 38 matches and different goal totals.

The gate's `_atletico_rows` (`factual_accuracy.py:106`) counts *newline-delimited* lines matching `ath?letico`, but `_mcp_result` serialises the standings as **compact single-line JSON** (`soccer_mcp.py:264`, `json.dumps` without indent). Both clubs share one line, so the gate counts 1 instead of 2 → `n_found = 18 + min(1,2) = 19`. Flamengo's record (which uses number extraction, not line counting) is checked correctly and passes.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source) | 280 (`soccer_mcp.py`) + 75 (tests) = 355 |
| Files (excl. data/artifacts) | 17 (source: 2 .py) |
| Dependencies | 0 (stdlib only) |
| Tests total | 10 |
| Tests effective | 10 |
| Skip ratio | 0% |
| Matches loaded | 23,954 |
| Steady request median | 238 ms (`_runtime.json`) |

## Findings

Top items (full list in `findings.jsonl`) — none at high+ severity:

1. [low] `factual_accuracy=0.5` is a gate row-counting artifact (single-line JSON), not a real defect — standings return both Atléticos.
2. [low] Match sources concatenated without dedup (23,954 = sum of 5 files); standings scopes to the dedicated Brasileirão file so 2019 answers stay correct.
3. [low] Dense multi-statement lines depress maintainability (0.256).

## Reproduce

```bash
cd "experiments/adrianco/experiment-57-factual-gate/brazil/runs/agent=codex_effort=default_language=python_model=gpt-5.6-luna_prompt=neutral/rep3"
cat scores.json _factual.json           # stored mechanical + factual scores
python3 -m unittest test_soccer_mcp -v   # optional: re-run tests (10 pass, 0 skip)
python3 -c "from soccer_mcp import SoccerDatabase as D; print(sorted(r['team'] for r in D().standings(2019)))"  # both Atléticos present
```
