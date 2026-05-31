# Brazilian Soccer MCP Server

An **MCP (Model Context Protocol) server** that provides a knowledge-graph
interface over Brazilian soccer datasets. It lets an LLM answer natural-language
questions about players, teams, matches and competitions, computing standings
and statistics directly from the bundled Kaggle data.

See `TASK.md` / `brazilian-soccer-mcp-guide.md` for the full specification.

## What was built

A Python package, `brazilian_soccer_mcp`, with a clean separation between the
(dependency-free) query engine and the MCP transport layer:

| Module | Responsibility |
|--------|----------------|
| `normalize.py` | Team-name normalization (state suffixes, accents, spelling and full-name aliases), competition canonicalization, multi-format date parsing |
| `models.py` | `Match` and `Player` dataclasses |
| `loader.py` | Loads all six CSV files into normalized records |
| `knowledge_graph.py` | `SoccerKnowledgeGraph` — indexed in-memory store answering every required query category |
| `formatters.py` | Turns query results into the human-readable answer style from the spec |
| `server.py` | `FastMCP` server exposing the graph as MCP tools |

### Data handling highlights

* **Six datasets unified.** `Brasileirao_Matches`, `novo_campeonato_brasileiro`
  (historical 2003-2019), `Brazilian_Cup_Matches`, `Libertadores_Matches`,
  `BR-Football-Dataset` (extended stats, multiple divisions) and `fifa_data`.
* **Deduplication.** Matches that appear in more than one dataset (e.g. a 2019
  Série A game present in both `Brasileirao_Matches` and the historical file)
  are collapsed by `(date, teams, score)`, so standings are computed exactly
  once. The 2019 Série A table correctly yields 20 teams and Flamengo as
  champion with 90 pts (28W 6D 4L), matching the official result.
* **Team-name normalization.** `Palmeiras-SP`, `Palmeiras` and
  `Sociedade Esportiva Palmeiras` all map to the same team; accents
  (`Grêmio`/`Gremio`) and spelling variants (`Athletico`/`Atletico`) are
  unified. Genuinely distinct clubs that share a base name
  (`Atlético-MG` vs `Atlético-PR`) are kept apart via their state code.
* **Competition matching is precise.** A query for "Brasileirão" resolves to
  Série A only and never leaks into Série B/C/D.

## MCP tools

| Tool | Description |
|------|-------------|
| `find_matches` | Matches by team, opponent, competition, season, venue or date range |
| `head_to_head` / `compare_teams` | Full head-to-head record between two teams |
| `team_record` | W/D/L, goals and win-rate for a team (optional season/competition/venue) |
| `standings` | League table computed from match results |
| `champion` | Table winner for a competition/season |
| `match_statistics` | Average goals, home/away/draw rates |
| `biggest_wins` | Largest-margin victories |
| `best_record` | Teams ranked by win rate (overall/home/away) |
| `search_players` | Players by name, nationality, club, position, min rating |
| `top_brazilian_players` | Highest-rated Brazilians |
| `players_at_club` | Squad list for a club |

## Usage

Install dependencies and run the server (stdio transport):

```bash
pip install -r requirements.txt
python run_server.py            # or: python -m brazilian_soccer_mcp.server
```

Example MCP client configuration:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "python",
      "args": ["run_server.py"],
      "cwd": "/path/to/this/repo"
    }
  }
}
```

The data directory is auto-detected (`data/kaggle`); override it with the
`BR_SOCCER_DATA` environment variable.

### Using the engine directly

```python
from brazilian_soccer_mcp import SoccerKnowledgeGraph

g = SoccerKnowledgeGraph.from_data_dir()
print(g.champion("Brasileirão", 2019).team)        # Flamengo
print(g.average_goals("Brasileirão")["avg_goals"]) # ~2.47
for p in g.top_brazilian_players(5):
    print(p.describe())
```

## Testing

BDD-style scenarios (Given-When-Then) implemented with PyTest cover loading,
normalization, all four query categories, statistical analysis, 20+ sample
questions and the MCP tool layer:

```bash
pip install -r requirements.txt
python -m pytest -q
```

All tests pass (the engine tests need no external dependencies; the MCP server
tests are skipped automatically if `mcp` is not installed).

## Data Sources

Kaggle data can't be downloaded without an account, so these (freely available
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
