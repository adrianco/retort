# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server, written in Elixir with **zero external
dependencies**, that answers natural-language questions about Brazilian soccer
from six Kaggle CSV datasets: matches (Brasileirão Série A 2003–2023, Copa do
Brasil, Copa Libertadores, plus extended statistics for Série A/B/C) and FIFA
player data.

Implemented per the specification in `TASK.md` / `brazilian-soccer-mcp-guide.md`.

## Architecture

```
lib/brazilian_soccer_mcp/
├── csv.ex          RFC 4180 CSV parser (quoted fields, CRLF, BOM) — no deps
├── team_names.ex   Team-name normalization: "Palmeiras-SP" / "Palmeiras" /
│                   "América - MG" / "A.s.a. - AL" / "Atlético Mineiro" all
│                   reduce to canonical keys; namesakes from different states
│                   (América-MG vs América-RN) stay distinct
├── match.ex        Match struct + helpers
├── player.ex       Player struct + position-group expansion
├── data_store.ex   Loads all 6 CSVs into memory (persistent_term), dedupes
│                   overlapping coverage across files on {date±1, home, away},
│                   merges extra stats (corners/shots/stadium) and fills
│                   missing scores from duplicate records
├── queries.ex      Match search, head-to-head, team stats, standings
│                   (3 pts/win, Brazilian tiebreakers), player search,
│                   biggest wins, aggregate statistics
├── format.ex       Human-readable answer formatting
├── tools.ex        MCP tool schemas + dispatch
├── server.ex       JSON-RPC 2.0 message handling (initialize, ping,
│                   tools/list, tools/call, notifications)
└── stdio.ex        Newline-delimited JSON-RPC stdio transport
                    (stdout = protocol only, diagnostics on stderr)
```

Uses Elixir 1.18+'s built-in `JSON` module, so `mix deps.get` is unnecessary
and the server works fully offline.

## Running

```sh
mix mcp.server                 # start the MCP server on stdio
# or build a standalone escript:
mix escript.build && ./brazilian_soccer_mcp
```

Register with an MCP client (e.g. Claude Code):

```sh
claude mcp add brazilian-soccer -- mix mcp.server
# (run from this project directory, or use --data-dir to point at data/kaggle)
```

Startup loads and indexes all ~25k match rows and 18k players in ~3 seconds;
queries then answer in milliseconds (well inside the < 2 s simple / < 5 s
aggregate requirement).

## Tools

| Tool | Purpose |
|------|---------|
| `search_matches` | Matches by team, opponent, competition, season, date range, stage |
| `head_to_head` | Full head-to-head record between two teams |
| `team_stats` | W/D/L, goals, win rate; venue filter; per-competition breakdown |
| `league_standings` | Season table computed from results (champion, relegation zone) |
| `search_players` | FIFA players by name/nationality/club/position/rating |
| `top_players` | Highest-rated players for a nationality/club/position |
| `biggest_wins` | Largest winning margins, filterable |
| `competition_stats` | Match counts, average goals, home/draw/away rates |
| `list_teams` | Discover canonical team names |

Example (2019 title question):

```
> league_standings {"season": 2019}
2019 Brasileirão Série A Standings (calculated from matches):
 1. Flamengo - 90 pts (28W, 6D, 4L, GD +49, GF 86) - Champion
 2. Santos - 74 pts (22W, 8D, 8L, GD +27, GF 60)
 ...
```

## Data-quality handling

- **Team name variations**: state suffixes in three styles (`-SP`, ` - MG`,
  ` MG`), official long names, punctuated acronyms (`A.s.a.`), renames
  (Atlético-PR → Athletico Paranaense), club-type words (`EC`, `FC`), and
  country codes for international clubs (`Nacional (URU)`, `Barcelona-EQU`)
  are all normalized; known data errors are corrected (Vitória listed as
  UF "ES", Bahia as "BH").
- **Overlapping files**: the same real match can appear in up to three files,
  sometimes dated ±1 day apart (timezones); records are deduplicated with a
  source-priority order so a 380-game season counts exactly 380 matches, and
  postponed fixtures missing scores in one file take their result from another.
- **Date formats**: ISO date, ISO datetime, and Brazilian `DD/MM/YYYY` all parse.
- **UTF-8**: accented text is preserved end-to-end; the stdio transport reads
  and writes raw bytes so multi-byte characters survive the JSON-RPC round trip.
- **FIFA licensing gaps**: FIFA 19 omits some Brazilian clubs (Flamengo,
  Palmeiras, Corinthians, São Paulo); player queries for them explain the gap
  instead of failing.

## Testing

BDD (Given/When/Then) ExUnit suite — 83 tests:

```sh
mix test
```

- `test/csv_test.exs` — CSV parser edge cases
- `test/team_names_test.exs` — name normalization across all dataset styles
- `test/data_store_test.exs` — all 6 files load; dedup correctness; encodings
- `test/queries_test.exs` — the specification's Gherkin scenarios (match search
  between two teams, team statistics per season) plus standings verified
  against real results (Flamengo 90 pts in 2019, Cruzeiro champion 2003)
- `test/server_test.exs` — MCP protocol: initialize/ping/tools list+call,
  JSON-RPC error codes (-32700/-32601/-32602), notifications
- `test/sample_questions_test.exs` — 26 sample questions from the spec
  answered through the tools, plus the < 2 s / < 5 s performance criteria
- `test/stdio_integration_test.exs` — real subprocess session over stdio

## Data Sources

Kaggle data can't be downloaded without an account so these (freely available
with attribution) data sets have been downloaded for use here:

https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro
- License: Attribution 4.0 International (CC BY 4.0)
- data/kaggle/Brasileirao_Matches.csv
- data/kaggle/Brazilian_Cup_Matches.csv
- data/kaggle/Libertadores_Matches.csv

https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches
- License: CC0: Public Domain
- data/kaggle/BR-Football-Dataset.csv

https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019
- License: World Bank - Attribution 4.0 International (CC BY 4.0)
- data/kaggle/novo_campeonato_brasileiro.csv

https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data
- License: Apache 2.0
- data/kaggle/fifa_data.csv
