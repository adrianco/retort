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

## Implementation (Clojure)

An MCP server (JSON-RPC 2.0 over stdio) that answers natural-language-friendly queries about the Brazilian soccer datasets in `data/kaggle/`.

### Requirements
- Clojure CLI 1.11+ and a JDK 11+ (dependencies are fetched from Maven on first run)

### Run
```sh
clojure -M:server                 # loads data/kaggle (or $BSM_DATA_DIR, or a path argument)
clojure -M:test                   # runs the test suite
```

### Tools
| Tool | Purpose |
|------|---------|
| `search_matches` | Matches by team, opponent, venue, competition, season or date range (most recent first) |
| `team_record` | Wins/draws/losses, goals and win rate for a team, filtered by season, competition or venue |
| `head_to_head` | Head-to-head record between two teams |
| `standings` | League table for a competition and season, calculated from results |
| `match_stats` | Goals per match, home/draw/away win rates, biggest wins |
| `search_players` | FIFA players by name, nationality, club, position group or minimum overall |

### Connecting to an MCP client
```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "clojure",
      "args": ["-M:server"],
      "cwd": "/absolute/path/to/this/repo"
    }
  }
}
```

### Data handling
- The five match files are loaded and de-duplicated: the 2012-2019 Brasileirão appears in several sources, and sources disagree on dates by a day for some fixtures, so duplicates are identified by competition, season and ordered team pair.
- Team names are normalized for accents, case, state suffixes (`Palmeiras-SP`, `Botafogo RJ`, `Boavista ... - RJ`), country codes (`Nacional (URU)`) and known alias/renamed clubs (e.g. Atlético-PR → Athletico).
- Known limitations: no top-scorer data (the files have no goal-scorer records); the FIFA file contains no Flamengo or São Paulo players; teams sharing a base name (e.g. Atlético-GO and Atlético-MG) are merged in standings when the state is absent.
