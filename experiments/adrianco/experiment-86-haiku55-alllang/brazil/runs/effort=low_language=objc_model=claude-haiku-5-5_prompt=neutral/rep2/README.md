# Brazilian Soccer MCP with spec and basic data sets

## Specification
brazilian-soccer-mcp-guide.md

## Implementation (Objective-C)

An MCP server written in Objective-C with only Foundation, so there's nothing to install beyond the Xcode command-line tools.

```sh
make            # builds build/brazilian-soccer-mcp
make test       # builds and runs the test suite against tests/fixtures and data/kaggle
```

Run the server (speaks newline-delimited JSON-RPC over stdio):

```sh
build/brazilian-soccer-mcp /absolute/path/to/data/kaggle   # or set BSM_DATA_DIR
```

Claude Desktop / Claude Code config:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/build/brazilian-soccer-mcp",
      "args": ["/absolute/path/to/data/kaggle"]
    }
  }
}
```

### Layout
- `src/BSCSVParser` — RFC 4180 CSV parsing (quotes, CRLF, UTF-8 BOM).
- `src/BSTextUtils` — team-name normalization (state suffixes, parentheticals, accents, aliases), date normalization (ISO and DD/MM/YYYY), competition names.
- `src/BSDataStore` — loads all six files, merges the match files into one list, and removes cross-file duplicates (same teams and score, date within one day).
- `src/BSQueryEngine` — match search, head-to-head, team records, standings, league statistics, rankings, player search, cross-file team profile.
- `src/BSMCPServer`, `src/BSMCPTools` — MCP protocol handling and the tools.
- `tests/` — BDD-style scenarios (`BS_SCENARIO("Feature", "Scenario")`) run by a small built-in harness, with hand-checked fixtures in `tests/fixtures`.

### Tools
| Tool | Purpose |
|------|---------|
| `search_matches` | Matches by team, opponent, venue, season, competition, date range, or stage |
| `head_to_head` | Rivalry record and recent meetings |
| `team_stats` | Wins/draws/losses, goals, win rate (season, competition, venue filters) |
| `standings` | League table calculated from results (3 pts per win) |
| `team_rankings` | Teams ranked by win rate at home/away/any venue |
| `league_stats` | Goals per match and home/draw/away rates |
| `biggest_wins` | Largest winning margins |
| `search_players` | FIFA player search by name, nationality, club, position, rating |
| `team_profile` | Cross-file: match record per competition plus the FIFA squad |

Natural-language questions are handled by the connected LLM, which chooses tools and arguments. The server does not parse free text.

### Known limitations
- Team matching is alias-based. Bare "Atletico" is treated as Atlético-MG, and only the aliases in `BSTeamAliases` are recognized beyond the generic normalization.
- The 2023 season exists only in `BR-Football-Dataset.csv`; the curated Brasileirão files end in 2022.
- Cross-file deduplication uses teams, score, and date ±1 day. Two genuinely different matches with the same score within a day would be merged.

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
