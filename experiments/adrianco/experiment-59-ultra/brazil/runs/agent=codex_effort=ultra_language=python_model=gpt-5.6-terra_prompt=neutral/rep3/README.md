# Brazilian Soccer MCP Server

An offline Python [Model Context Protocol](https://modelcontextprotocol.io) server over the six bundled Brazilian soccer CSV datasets. It answers match, team, player, competition, derby, standings, and statistical questions without calling a third-party API.

## Run it

```bash
python -m pip install -r requirements.txt
python server.py
```

The server uses stdio, so configure an MCP client with a command equivalent to:

```json
{
  "command": "python",
  "args": ["/absolute/path/to/server.py"]
}
```

The data directory defaults to `data/kaggle/` beside the code. Set `BRAZILIAN_SOCCER_DATA_DIR` to point at another directory containing the same six files.

## MCP tools

| Tool | What it does |
| --- | --- |
| `ask_soccer` | Handles common natural-language questions, returning a concise answer plus structured evidence. |
| `search_matches` | Filters by team, home/away side, opponent, season, date range, competition, stage, round, or source. |
| `get_team_statistics` | Computes W/D/L, goals, points, and win rate for overall, home, or away fixtures. |
| `compare_teams` | Produces a head-to-head record and recent meetings. |
| `search_players` | Searches the bundled FIFA snapshot by name, nationality, club, position, or rating. |
| `get_standings` / `get_relegated_teams` | Calculates season tables and bottom positions from supplied results. |
| `get_competition_statistics` / `get_biggest_wins` | Calculates goals, home advantage, and largest margins. |
| `get_competition_bracket` | Groups Libertadores or Cup fixtures by stage/round. |
| `get_team_competitions`, `search_derbies`, `get_entity_relationships` | Explore the graph of teams, players, opponents, and competitions. |
| `list_available_data` | Verifies coverage and explains data-source modes. |

For exact, composable use, call the structured tools. For example, `search_matches(team="Flamengo", opponent="Fluminense")` returns machine-readable fixtures; `ask_soccer("When did Flamengo last play Corinthians?")` returns the same sort of evidence with a short answer.

## Data semantics

All six supplied files are loaded using UTF-8/BOM-safe CSV parsing:

- `Brasileirao_Matches.csv`
- `Brazilian_Cup_Matches.csv`
- `Libertadores_Matches.csv`
- `BR-Football-Dataset.csv`
- `novo_campeonato_brasileiro.csv`
- `fifa_data.csv`

The match feeds overlap. Searches and aggregates therefore accept `dataset_mode`:

- `canonical` (default): a documented preferred source per competition/year, avoiding duplicate fixtures in records and standings.
- `all`: every input row, useful for source exploration.
- `unique`: cross-source de-duplicated fixtures retaining every contributing source filename.

Team matching is case-, accent-, and punctuation-insensitive, while preserving meaningful state identities. For example, `São Paulo`, `Sao Paulo-SP`, and `São Paulo - SP` match; `Atlético-MG`, `Atlético-GO`, and `Athletico-PR` remain distinct. Unknown scores (`NA` or `-`) are returned by match search but excluded from calculated W/D/L, standings, and goal averages.

The FIFA dataset is a historical snapshot, not a live roster. Empty results are returned honestly rather than supplemented from external sources.

## Test

```bash
python -m pytest
```

The test suite uses Given/When/Then-style scenarios over the actual bundled data, including source coverage, date parsing, normalization, null-score handling, player search, standings, and natural-language routing.

## Dataset attribution

The bundled data retains the sources and licenses documented in `TASK.md`:

- Brazilian league, Copa do Brasil, and Libertadores data: Kaggle `ricardomattos05/jogos-do-campeonato-brasileiro` (CC BY 4.0).
- Extended football data: Kaggle `cuecacuela/brazilian-football-matches` (CC0).
- Historical Brasileirão data: Kaggle `macedojleo/campeonato-brasileiro-2003-a-2019` (CC BY 4.0).
- FIFA player data: Kaggle `youssefelbadry10/fifa-players-data` (Apache 2.0).
