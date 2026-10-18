# Brazilian Soccer MCP with spec and basic data sets

## Specification
brazilian-soccer-mcp-guide.md

## Data Sources
Kaggle data can't be downloaded without an account so these (freely available with attribution) data sets have been downloaded for use here:

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

## Implementation: Elixir MCP server

An [MCP](https://modelcontextprotocol.io) server (stdio transport, JSON-RPC 2.0)
that answers natural-language questions about the datasets above. The LLM
client calls one of six tools; the server answers with plain text.

### Build, test, run

```sh
mix deps.get
mix test                      # 78 tests (incl. 7 doctests): BDD-style, plus real-data checks
mix escript.build             # produces ./soccer_mcp
./soccer_mcp --data-dir data/kaggle
```

The data directory defaults to `data/kaggle` (or `$SOCCER_DATA_DIR`). Load
summaries go to stderr; stdout carries only protocol lines.

Example client configuration:

```json
{ "mcpServers": { "brazilian-soccer": { "command": "/path/to/soccer_mcp", "args": ["--data-dir", "/path/to/data/kaggle"] } } }
```

### Tools

| Tool | Answers |
|------|---------|
| `search_matches` | Matches by team, opponent, competition, season, venue, stage (e.g. `final`), date range; head-to-head summary when two teams are given |
| `team_stats` | Wins, draws, losses, goals, win rate for a team (optionally by competition, season, venue) |
| `head_to_head` | Record between two teams across all competitions |
| `competition_standings` | League table for a Brasileirão season, calculated from results |
| `search_players` | FIFA players by name, nationality, club, position, minimum overall |
| `match_statistics` | `averages`, `biggest_wins`, `best_home`, `best_away` |

### Layout

- `lib/soccer_mcp/csv.ex`: RFC 4180 reader (BOM, CRLF, quoted fields)
- `lib/soccer_mcp/team.ex`: team name normalization (state suffixes, accents, aliases such as `Sport Club Corinthians Paulista` → `corinthians`)
- `lib/soccer_mcp/parse.ex`: ISO, dotted and Brazilian dates; numeric fields
- `lib/soccer_mcp/store.ex`: loads all six files; de-duplicates matches listed in more than one file; labels Copa do Brasil finals
- `lib/soccer_mcp/query.ex`: pure queries (filters, records, standings, averages, rankings, player search)
- `lib/soccer_mcp/tools.ex`: tool schemas and argument handling; bad input returns a readable error
- `lib/soccer_mcp/server.ex`: JSON-RPC / MCP methods (`initialize`, `tools/list`, `tools/call`, `ping`)
- `test/soccer/`: BDD-style tests; `fixtures/` holds small CSVs with the real column layouts; `real_data_test.exs` runs against `data/kaggle`

### Data decisions and known limitations

- **Duplicates.** The Brasileirão files overlap (2012–2019 appear in more than
  one), and the extended file repeats some matches with dates a day or two
  apart. Two rows are the same match when competition, season and ordered
  home/away teams agree, dates are within 3 days and states do not conflict.
  The result is 17,545 matches; 2019 Série A has the expected 380.
- **Clubs with the same short name.** Team keys drop state suffixes, so a bare
  query such as `Atletico` matches both Atlético-MG and Atlético-PR. Include
  the state (`Atletico-GO`) to pick one; standings label same-named clubs with
  their state. Venue rankings do not yet separate them.
- **Copa do Brasil finals.** The data has no stage label for finals. A final is
  taken to be the last numbered round of a season when that round has at most
  two matches (two-legged). This gives two per season for 2012–2020; the 2021
  file has no such round, so no finals are labelled for that year.
- **Extended file.** Its 2022–2023 rows carry no round, so cup rounds are unknown there.
- **Player data.** The FIFA file has no Flamengo (or other Brazilian club)
  players, so club searches for those return no results.
- **Name display.** Display names come from the first source seen, so a club may
  appear with a variant spelling (e.g. "Atletico (PR)" rather than "Athletico (PR)").
- Start-up loads all files in about 2.5 seconds. A real-data test checks that
  league averages and standings finish within the 5-second aggregate budget.
