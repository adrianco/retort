# Evaluation: language=rust_model=sonnet_prompt=ATDD · rep 1

## Summary

- **Factors:** language=rust, model=sonnet, prompt=ATDD
- **Status:** ok — builds and all tests pass, but two high-severity correctness defects survive the suite
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, R1–R12)
- **Tests:** 12 passed / 0 failed / 0 skipped (12 effective) — `test_coverage=1.0` from `scores.json`
- **Build:** pass — `test_coverage=1.0` / `defect_rate=0.961` (scores.json; not re-run)
- **Lint:** pass — `code_quality=0.833` (scores.json proxy)
- **Architecture:** see `summary/index.md`
- **Findings:** 7 items in `findings.jsonl` (0 critical, 2 high, 2 medium, 2 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing query tools | ✓ implemented | `src/main.rs:170-211` JSON-RPC `initialize`/`tools/list`/`tools/call`; 6 tools in `tools_list()` (hand-rolled, no SDK); test `tools_list_exposes_all_required_tools` |
| R2 | Loads provided data/kaggle/ datasets | ✓ implemented | `src/data.rs:1009-1081` loads all 6 CSVs into `AppData` |
| R3 | Match query by team (home/away/either) | ✓ implemented | `src/tools.rs:246-288` `find_matches` via `teams_match` on both sides; tests `find_matches_between_*`, `team_name_normalization` |
| R4 | Filter by date range and/or season | ✓ implemented | `src/tools.rs:243,283` season filter (satisfies "and/or"); test `find_matches_by_season`. Note: explicit date-range filter absent (low finding R4) |
| R5 | Filter by competition (3 comps) | ✓ implemented | `src/tools.rs:267-281` maps brasileirao/copa_brasil/libertadores across source files |
| R6 | Team W/L/D + goals for/against | ✓ implemented | `src/tools.rs:345-459` `get_team_stats`; test `get_team_stats_returns_win_loss_draw` |
| R7 | Player search by name | ✓ implemented | `src/tools.rs:485` name filter in `find_players` |
| R8 | Filter players by nationality/club + ratings | ✓ implemented | `src/tools.rs:488-494` nationality/club/position + overall; tests `find_players_by_nationality_brazil`, `find_players_by_club` |
| R9 | Season standings computed from matches | ✓ implemented | `src/tools.rs:698-824` `get_standings` builds points table from results; test `get_standings_brasileirao_2019`. ⚠ numbers inflated by BUG1 |
| R10 | Aggregate statistics | ✓ implemented | `src/tools.rs:843-969` avg goals, home/away win rates, biggest win; test `get_statistical_summary_brasileirao` |
| R11 | Head-to-head between two teams | ✓ implemented | `src/tools.rs:583-695` `get_head_to_head`; test `get_head_to_head_corinthians_palmeiras` |
| R12 | Automated tests covering queries | ✓ implemented | `tests/acceptance.rs` 10 black-box tests + 2 unit tests in `normalize.rs`; `test_coverage=1.0` |

**Prompt (ATDD) conformance:** ✓ Followed. `tests/acceptance.rs` drives the *compiled binary* over the MCP protocol via stdin/stdout (`McpTestServer`, lines 9-77) — external-user perspective, public interface only, no back-door access, each scenario on a fresh server process (independent). This is genuine executable ATDD. Weakness: several assertions are thin (non-empty / "contains a digit") and coupled to live dataset values, which is why BUG1/BUG2 pass the suite (finding Q2).

## Build & Test

Not re-run — stored mechanical scores reused per skill policy.

```text
scores.json
  test_coverage = 1.0   (build succeeded + all tests passed)
  defect_rate   = 0.961
  code_quality  = 0.833
  maintainability = 0.258
  idiomatic     = 0.72
  token_efficiency = 0.096
```

```text
test inventory (grep)
  #[test] markers: 12  (10 acceptance in tests/acceptance.rs + 2 unit in src/normalize.rs)
  #[ignore]/skip markers: 0  → 12 effective tests, 0 skipped
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 1,428 (`src/`) + 264 (`tests/`) = 1,692 |
| Files (excl. target/data) | 15 |
| Dependencies | 4 (serde, serde_json, csv, tokio) |
| Tests total | 12 |
| Tests effective | 12 |
| Skip ratio | 0% |
| Build duration | n/a (reused scores, not re-run) |

Note: `tokio` is declared with `features=["full"]` but the server uses a blocking stdin loop — the async runtime appears unused (minor).

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [high] BUG1 — Overlapping Brasileirão datasets merged without dedup: the same 380 matches for 2019 exist in three loaded files, so standings/team-stats/summary triple-count (`src/data.rs:1009-1069`).
2. [high] BUG2 — `truncate()` byte-slices UTF-8 (`src/tools.rs:574-580`); 28 player rows (club "San Martin de Tucumán") split a multibyte char at byte 20 → server panic mid-session.
3. [medium] Q1 — Competition-filter ladder duplicated across 4 tools (`src/tools.rs:268,366,611,707`); drives low maintainability (0.258).
4. [medium] Q2 — Acceptance assertions weak/data-coupled, so BUG1's tripled points pass undetected (`tests/acceptance.rs:163,176,255`).
5. [low] R4 — Season filter present but no explicit date-range parameter (`src/tools.rs:243`).

## Reproduce

```bash
cd experiment-14/runs/language=rust_model=sonnet_prompt=ATDD/rep1
cat scores.json                                   # reuse stored build/test/lint scores
grep -rE "#\[test\]" src tests                    # 12 tests
grep -rE "#\[ignore\]" src tests | wc -l          # 0 skips
# BUG1 — overlapping seasons (each prints 380):
python3 - <<'PY'
import csv,collections
for f,idx in [("data/kaggle/Brasileirao_Matches.csv",7),("data/kaggle/novo_campeonato_brasileiro.csv",2)]:
    c=collections.Counter()
    for r in csv.reader(open(f,encoding='utf-8',errors='replace')): 
        try:c[r[idx][:4]]+=1
        except:pass
    print(f, "2019:", c.get('2019'))
PY
# BUG2 — accented club name splits at byte 20:
python3 -c "s='San Martin de Tucumán'.encode(); print('continuation byte at 20:', (s[20]&0xC0)==0x80)"
```
