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

## Implementation

A stdlib-only Python MCP server (`brazsoccer_mcp/`) that loads the six CSV files in `data/kaggle/` into memory and answers questions through MCP tools over stdio (JSON-RPC 2.0).

- `normalize.py`: team-name keys (strips `-SP` / `(antigo ...)` / `FC` / `EC`, ignores accents, applies known aliases, uses state codes to split Atlético-MG from Athletico-PR), date parsing (ISO, ISO datetime, `DD/MM/YYYY`) and number parsing.
- `loaders.py`: one loader per file. Unplayed or malformed rows (`NA`, `-`) are skipped and counted in a `LoadReport`.
- `store.py`: `SoccerData`, the query layer. It removes fixtures that appear in more than one file (same competition, pair and score, dates within one day) and resolves fuzzy team and competition names.
- `tools.py`: the MCP tools: `find_matches`, `head_to_head`, `team_stats`, `standings`, `league_stats`, `best_away_records`, `search_players`, `brazilian_players_by_club`.
- `mcp_server.py` / `__main__.py`: the stdio server.

### Run

```sh
python3 -m brazsoccer_mcp                     # serves MCP on stdin/stdout
python3 -m brazsoccer_mcp --data-dir PATH     # or set BRAZSOCCER_DATA_DIR
```

Example client configuration:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "python3",
      "args": ["-m", "brazsoccer_mcp"],
      "cwd": "/path/to/this/repo"
    }
  }
}
```

### Test

```sh
pip install -r requirements-dev.txt
python3 -m pytest
```

Tests are plain pytest with Given/When/Then comments and docstrings, not a Gherkin runner. They cover name and date normalization, loader skip behaviour, queries against the real data (including the 2019 champion table), and the JSON-RPC protocol.

### Known limitations

- The 2023 league file has 377 rows, one fixture short of a full season.
- Top scorers are not included because the datasets have no goal events.
- There is no natural-language parser. The connected LLM chooses the tool and arguments.
- The `Serie B` and `Serie C` rows from the extended file are loaded but only reachable by their exact competition name.
