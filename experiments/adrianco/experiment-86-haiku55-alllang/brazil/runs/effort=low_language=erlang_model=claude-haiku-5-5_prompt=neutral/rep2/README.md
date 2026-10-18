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

## Implementation (Erlang)

An MCP server (stdio, JSON-RPC 2.0) that answers natural-language soccer questions by letting an LLM call typed query tools over the six CSV datasets. No third-party dependencies: JSON uses OTP's built-in `json` module (OTP 27+).

### Build, test, run

```sh
rebar3 eunit                      # 72 tests: unit, query, MCP protocol and BDD acceptance
rebar3 escriptize                 # builds _build/default/bin/brazil_soccer_mcp
_build/default/bin/brazil_soccer_mcp data/kaggle
```

The data directory is the first argument, or `$BSM_DATA_DIR`, or `data/kaggle`. Run tests from the project root (or set `BSM_DATA_DIR`) because the BDD and protocol tests load the real CSVs.

Example MCP client configuration:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/_build/default/bin/brazil_soccer_mcp",
      "args": ["/absolute/path/to/data/kaggle"]
    }
  }
}
```

### Tools

| Tool | Purpose |
|------|---------|
| `find_teams` | Resolve a partial or accented name to canonical teams before querying |
| `search_matches` | Matches by team, opponent (head-to-head), competition, season, date range and venue |
| `team_record` | W/D/L, goals for/against, goal difference and win rate |
| `head_to_head` | Two-team record with recent meetings |
| `standings` | Brasileirão Série A table for a season (3/1/0 points; ties by wins, goal difference, goals) |
| `league_stats` | Average goals per match, home/draw/away percentages, biggest wins |
| `search_players` | FIFA player search by name, nationality, club, position, minimum overall |

### Layout

- `src/bsm_csv.erl` RFC 4180 parser (quotes, CRLF, BOM)
- `src/bsm_team.erl` team-name normalisation (state suffixes, parentheticals, club prefixes, accents, aliases)
- `src/bsm_date.erl` ISO and `DD/MM/YYYY` dates
- `src/bsm_loader.erl` loads all six files into one match list; de-duplicates overlapping sources
- `src/bsm_store.erl` holds the read-only dataset in `persistent_term`
- `src/bsm_query.erl` pure query and statistics functions
- `src/bsm_tools.erl` tool schemas, argument handling and JSON output
- `src/bsm_mcp.erl` JSON-RPC/MCP loop
- `features/brazilian_soccer.feature` Gherkin scenarios; `test/bsm_bdd_tests.erl` implements them

### Data issues handled

- **Overlapping sources.** Brasileirão 2012–2019 appears in both `Brasileirao_Matches.csv` and `novo_campeonato_brasileiro.csv`. The BR-Football feed repeats Serie A and Copa do Brasil again. Duplicates are identified by competition, season, both teams and the score, then confirmed with state-aware team matching, so the same pairing with a different score or state is never merged. Dates are not part of the key because the BR-Football feed is sometimes a day off.
- **Team names.** BR-Football uses names such as `EC Bahia`, `Fortaleza FC`, `Atletico Mineiro`, `Sport Recife` and `Botafogo RJ`. These are normalised to the same club as the other feeds.
- **Bad state code.** `novo_campeonato_brasileiro.csv` lists Bahia as `BH`. Two-letter codes that are not Brazilian UFs are treated as unknown.
- **Coverage gaps.** Serie A 2023 exists only in the BR-Football feed (377 matches). Serie A 2003 has 552 matches in the source file. `fifa_data.csv` has no players listed at Flamengo, so club searches for that club return nothing.

### Verified figures

- Brasileirão 2019 table: Flamengo 90 pts (28W 6D 4L), Santos 74, Palmeiras 74, matching the spec's example.
- Serie A 2012 and 2019 each contain 380 matches after de-duplication.
