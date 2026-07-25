# Evaluation: language=c · model=claude-fable-5 · prompt=neutral · rep 1

## Summary

- **Factors:** language=c, model=claude-fable-5, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, R1–R12)
- **Tests:** 75 assertions + ≥20 sample-question gate, all pass / 0 failed / 0 skipped (75+ effective)
- **Build:** pass — `test_coverage=1.0`, `defect_rate=1.0` (from `scores.json`)
- **Lint:** pass — `code_quality=1.0` (from `scores.json`), built `-Wall -Wextra -std=c11`
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

A dependency-free C11 MCP server (~2,890 LOC, 9 files) with its own CSV and JSON
implementations. Every pinned requirement is backed by a registered MCP tool and
an executing test. Mechanical scores are perfect (`code_quality`, `test_coverage`,
`defect_rate` all 1.0); the only lower scores are `token_efficiency` (0.013 — a
large hand-rolled codebase) and `maintainability` (0.454), neither of which is a
conformance gate. The `neutral` prompt prescribes no methodology beyond "include
tests," so there are no extra `P*` requirements to check.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing tools/handlers | ✓ implemented | `mcp_main.c` JSON-RPC 2.0 stdio (`initialize`/`tools/list`/`tools/call`); `TOOLS[]` in `tools.c:827`, 7 tools |
| R2 | Loads provided `data/kaggle/` datasets | ✓ implemented | `data.c:552-557` `db_load` loads 5 match CSVs + `fifa_data.csv`; test asserts exact row counts |
| R3 | Match query by team (home/away/either) | ✓ implemented | `tool_search_matches` `tools.c:229` `team`/`opponent` filters via `collect()` |
| R4 | Filter by date range and/or season | ✓ implemented | `search_matches` `season`/`date_from`/`date_to`; `parse_date_ymd` in `data.c` |
| R5 | Filter by competition (Brasileirão/Copa/Libertadores) | ✓ implemented | `comp` filter spans SRC_BRASILEIRAO/COPA/LIB/NOVO/BRF; schema `tools.c:840` |
| R6 | Team W/L/D record + goals for/against | ✓ implemented | `tool_get_team_stats` `tools.c:329`, `Rec{p,w,d,l,gf,ga}` + win rate, home/away split |
| R7 | Player search by name | ✓ implemented | `tool_search_players` `tools.c:494` `name` filter; test finds "Casemiro"/"Neymar" |
| R8 | Filter players by nationality/club + ratings | ✓ implemented | `search_players` `nationality`/`club`/`position`/`min_overall`, sorted by overall |
| R9 | Season standings computed from match results | ✓ implemented | `tool_get_standings` `tools.c:608` (3 pts/win, champion + relegation); test asserts Flamengo 90 pts 2019 |
| R10 | Aggregate statistics | ✓ implemented | `tool_get_league_stats` `tools.c:693`: goals/match, home/draw/away rates, biggest wins |
| R11 | Head-to-head between two teams | ✓ implemented | `tool_head_to_head` `tools.c:420` + h2h summary in `search_matches`; test compares Palmeiras/Santos |
| R12 | Automated tests covering query capabilities | ✓ implemented | `test_main.c` 75 `check()` asserts + `test_mcp.sh` protocol test; `test_coverage=1.0` |

## Build & Test

Scores read from `scores.json` (not re-run, per skill):

```text
{"code_quality": 1.0, "test_coverage": 1.0, "defect_rate": 1.0,
 "maintainability": 0.454, "idiomatic": 0.7, "token_efficiency": 0.0133}
```

```text
make test   # ./test_bsmcp data/kaggle && sh test_mcp.sh
75 check() assertions, 0 failed  (test_coverage=1.0)
Includes: db_load of all 6 files with exact row counts (4180/1337/1255/10296/6886
matches, 18207 players), name normalization/accents, date parsing, every tool,
"≥20 sample questions answered", slowest query <2s, aggregate <5s.
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 2,890 (`*.c` + `bsmcp.h`) |
| Files (source) | 9 (`*.c`, `.h`, `.sh`, `Makefile`) |
| Dependencies | 0 (libc only) |
| Tests total | 75 `check()` + ≥20 sample-question gate |
| Tests effective | 75+ (0 skipped) |
| Skip ratio | 0% |
| Build duration | not re-run (scores from `scores.json`) |

## Findings

No critical/high/medium/low findings. 3 info-level observations (full list in `findings.jsonl`):

1. [info] R9 standings scoped to Brasileirão Série A/B/C (cup competitions are knockout) — spec-satisfying.
2. [info] FIFA player data is a single FIFA 19 snapshot — dataset property, not a defect.
3. [info] Queries are in-memory linear scans; performance gates (<2s / <5s) still pass.

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiments/adrianco/experiment-48-fable5-gaps/brazil/runs/language=c_model=claude-fable-5_prompt=neutral/rep1
cat scores.json                 # perfect code_quality/test_coverage/defect_rate
make test                       # ./test_bsmcp data/kaggle && sh test_mcp.sh
grep -n 'TOOLS\[\]' tools.c     # 7 registered MCP tools
grep -nE 'LOADF' data.c         # 6 Kaggle CSVs loaded
```
