# Brazilian Soccer MCP Server

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server that
answers natural-language questions about Brazilian soccer — matches, teams,
players, competitions and statistics — over the pre-downloaded Kaggle datasets
in `data/kaggle/`. Built test-first (TDD) with pure-Python data loading (no
database required).

See [`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md) /
[`TASK.md`](TASK.md) for the full specification.

## Architecture

The code is layered so each concern is independently unit-tested:

| Module | Responsibility |
|--------|----------------|
| `brazilian_soccer/normalize.py` | Canonicalize team names (strip state/country suffixes, accents, casing; alias full names; **keep the state for ambiguous clubs** like Atlético-MG vs Atlético-PR). |
| `brazilian_soccer/data_loader.py` | Load the 6 CSVs into uniform `Match` / `Player` records, tolerant of mixed date formats, float-encoded goals and UTF-8/BOM. De-duplicates the two overlapping Brasileirão sources so each season comes from one authoritative file. |
| `brazilian_soccer/queries.py` | `KnowledgeBase` — the query engine: match search, head-to-head, team records, computed league standings, player search, and aggregate statistics. |
| `brazilian_soccer/tools.py` | `SoccerTools` — formats query results into the human-readable answers shown in the spec. |
| `brazilian_soccer/server.py` | Thin `FastMCP` server exposing each capability as an MCP tool. |

### Data-quality handling

* **Team-name variations** — `Palmeiras-SP`, `Palmeiras`, `Sociedade Esportiva
  Palmeiras` all normalize to one key. Genuinely distinct clubs that share a
  base name (Atlético-MG, Atlético-PR, Atlético-GO; América-MG, -RN, -RJ) are
  kept apart by their state code and mapped to canonical names.
* **Multiple date formats** — `2012-05-19 18:30:00`, `2023-09-24` and
  `29/03/2003` are all parsed.
* **Overlapping sources** — `Brasileirao_Matches.csv` (2012–2022) and
  `novo_campeonato_brasileiro.csv` (2003–2019) overlap on 2012–2019. The loader
  assigns each season to a single source (the historical file for ≤2019) so
  standings are not double-counted. Validated against the real 2019 table
  (Flamengo champions, 90 pts; Santos 2nd, Palmeiras 3rd on the wins tiebreaker).

## MCP tools

| Tool | Purpose |
|------|---------|
| `search_matches` | Find matches by team / opponent / venue / season / competition / date range. |
| `head_to_head` | Win-draw-goal record between two teams. |
| `team_record` | A team's W/D/L, goals and win rate (overall, home or away). |
| `standings` | League table for a season, computed from match results. |
| `search_players` | FIFA players by name / nationality / club / position / minimum rating. |
| `players_by_club` | Player counts and average rating grouped by club. |
| `statistics` | Average goals per match and home win rate. |
| `biggest_wins` | Largest-margin victories. |
| `best_record` | Teams ranked by home or away win rate. |
| `data_summary` | How much data is loaded, by competition. |

## Usage

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the MCP server (stdio transport):

```bash
python -m brazilian_soccer.server
```

Register it with an MCP client (e.g. Claude Desktop `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "python",
      "args": ["-m", "brazilian_soccer.server"],
      "cwd": "/path/to/this/repo"
    }
  }
}
```

Use the library directly:

```python
from brazilian_soccer.queries import KnowledgeBase
from brazilian_soccer.tools import SoccerTools

tools = SoccerTools(KnowledgeBase.load())
print(tools.standings(2019, "Brasileirão"))
print(tools.head_to_head("Palmeiras", "Santos"))
print(tools.search_players(nationality="Brazil", min_overall=85, limit=5))
```

## Tests

```bash
python -m pytest
```

60 tests cover normalization, loading, querying, formatting, the MCP wiring,
and an end-to-end suite that answers 20+ sample questions against the real data
and asserts the spec's performance budgets (simple < 2 s, aggregate < 5 s).

## Data Sources

Kaggle data can't be downloaded without an account, so these freely available
(with attribution) datasets are included under `data/kaggle/`:

- https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro
  — License: CC BY 4.0 — `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`
- https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches
  — License: CC0 Public Domain — `BR-Football-Dataset.csv`
- https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019
  — License: CC BY 4.0 — `novo_campeonato_brasileiro.csv`
- https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data
  — License: Apache 2.0 — `fifa_data.csv` (FIFA 19 export, 18,207 players)
