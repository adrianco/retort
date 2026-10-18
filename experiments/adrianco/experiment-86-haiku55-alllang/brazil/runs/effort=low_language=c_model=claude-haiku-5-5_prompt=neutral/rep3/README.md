# Brazilian Soccer MCP Server

A Model Context Protocol (MCP) server, written in plain C11 with no dependencies, that answers
questions about Brazilian soccer from the Kaggle datasets in `data/kaggle/`. An LLM client
calls its tools and turns the replies into natural-language answers. The specification is
[brazilian-soccer-mcp-guide.md](brazilian-soccer-mcp-guide.md).

## Build and test

```sh
make          # build/brazil-soccer-mcp
make test     # build/test_runner against data/kaggle (618 checks)
```

Requires a C11 compiler and `make`. Tested with Apple clang on macOS.

## Run

```sh
build/brazil-soccer-mcp [data_dir]    # default data/kaggle, or $BRAZIL_SOCCER_DATA
```

The server speaks JSON-RPC 2.0 over stdio, one message per line. Startup logs go to stderr.

Example MCP client entry:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/path/to/build/brazil-soccer-mcp",
      "args": ["/path/to/data/kaggle"]
    }
  }
}
```

## Tools

| Tool | Answers | Main arguments |
|------|---------|----------------|
| `search_matches` | Match lists, head-to-head totals | `team`, `opponent`, `competition`, `season`, `from`, `to`, `venue`, `limit` |
| `team_record` | Wins, draws, losses, goals, win rate | `team` (required), `season`, `competition`, `venue` |
| `standings` | League table calculated from results | `season` (required), `competition`, `limit` |
| `match_stats` | Goals per match, home/draw/away rates, biggest wins | `team`, `season`, `competition`, `venue`, `from`, `to` |
| `player_search` | FIFA players by name, nationality, club, position, rating | `name`, `nationality`, `club`, `position`, `min_overall`, `limit` |

`competition` is a case- and accent-insensitive substring, so `Brasileirao`, `Copa do Brasil`
and `Libertadores` all work. Dates accept `YYYY-MM-DD` or `DD/MM/YYYY`.

## What was built

- **Loading** (`src/dataset.c`): all six CSVs go through one column-mapped loader. Loading
  takes about 0.2 s on the development machine. Loaded: 17,128 unique matches and 18,207 players.
- **Team names** (`src/names.c`): each name becomes a base plus an optional state or country
  code. `Palmeiras-SP`, `Palmeiras` and `Sociedade Esportiva Palmeiras` resolve to the same
  club. State suffixes are split off, generic club words such as `FC` are dropped, and an alias
  table covers renamed or full-form clubs. `Atletico-PR` becomes `Athletico` because the club
  was renamed in 2019, while `Atletico-GO` and `Atletico-MG` stay separate.
- **Duplicates**: the Brasileirão file and the 2003–2019 file overlap, and the extended file
  repeats matches under other names. Fixtures with the same competition, teams and score, dated
  within one day of each other, are counted once. The highest-priority source is kept.
- **Standings and records** are calculated from match results. Nothing is hard-coded.
- **Encoding**: UTF-8 names, a BOM on `fifa_data.csv`, quoted CSV fields and CRLF line endings
  are all handled.

Check against the data: the 2019 Brasileirão table gives Flamengo 90 pts (28W 6D 4L),
Santos 74 and Palmeiras 74, which matches the examples in the spec.

## Source layout

```
src/util.*      buffer, allocation, string vector
src/csv.*       CSV loader
src/json.*      JSON parser and writer
src/names.*     accent folding, team-name normalisation, date and goal parsing
src/dataset.*   loads and cleans the six CSV files
src/query.*     filter engine: matches, records, standings, head-to-head, stats, players
src/tools.*     MCP tool schemas and text formatting
src/mcp.*       JSON-RPC envelope and method dispatch
src/main.c      stdio server loop
tests/test_main.c   Given/When/Then scenarios
```

## Known limitations

- **No top scorers.** The datasets have no goal-scorer data, so this cannot be answered.
- **No Flamengo players in the FIFA file.** `fifa_data.csv` lists almost no Brazilian clubs.
  Player queries for Brazilian clubs return few or no results. Brazilian players in the file
  are found through `nationality: Brazil`.
- **Clubs without a state code.** Some extended-file names carry no state, and when a club has
  more than one code in the data the code cannot be inferred. Those rows form a separate team.
- **Source noise.** A few rows carry odd codes, for example `Bahia-BH`.
- **Attribution.** The datasets are CC BY 4.0 (Brasileirão files) and CC0 (extended match file),
  Apache 2.0 (FIFA player data). See the links in the spec.
