# Brazilian Soccer MCP Server

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server that
answers natural-language questions about Brazilian soccer — players, teams,
matches, competitions and statistics — over the bundled Kaggle datasets.

The server is implemented in Python on top of `pandas`, exposes 11 tools through
the official `mcp` SDK (stdio transport), and ships with a CLI and a full test
suite. The full requirements are in [`TASK.md`](TASK.md) /
[`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md).

## What was implemented

| Layer | File | Responsibility |
|-------|------|----------------|
| Normalization | `bsoccer/normalize.py` | Canonicalize team names: strip accents (`São`→`Sao`), drop state/country suffixes (`Palmeiras-SP`→`Palmeiras`), resolve aliases (`Vasco`→`Vasco da Gama`), and keep ambiguous clubs distinct (`Atletico-MG` ≠ `Atletico-GO` ≠ `Athletico-PR`). |
| Data | `bsoccer/data.py` | Load all six CSVs into one unified, UTF-8-safe match table plus the FIFA player table; deduplicate the overlapping Brasileirão sources. |
| Queries | `bsoccer/queries.py` | `QueryEngine` answering the five capability categories. |
| Formatting | `bsoccer/format.py` | Render structured results as the prose shapes shown in the spec. |
| MCP server | `bsoccer/server.py` | `FastMCP` server exposing the engine as tools. |
| CLI | `bsoccer/cli.py` | Command-line front end for manual exploration / demos. |

Every source file opens with a context block comment describing its purpose.

## Data handling highlights

- **All 6 CSV files loaded** into a single normalized schema (23,800+ matches,
  18,200+ players).
- **Team-name normalization** handles the three naming conventions in the spec
  (suffix, no-suffix, full names) and the genuinely ambiguous "Atlético" /
  "América" clubs, which share a base name but are different teams.
- **Cross-file deduplication**: the Brasileirão appears in three files with
  overlapping seasons. `matches_dedup` collapses duplicates so standings and
  aggregates don't double-count — the 2019 Brasileirão correctly resolves to its
  380 matches and the real final table (Flamengo champions, 90 pts, 28W-6D-4L).
- **Multiple date formats** (`2012-05-19 18:30:00`, `29/03/2003`, `2023-09-24`)
  and UTF-8 Portuguese text are parsed correctly.

## Installation

```bash
pip install -r requirements.txt      # mcp, pandas, pytest
# or, to install as a package with entry points:
pip install -e .
```

## Running the MCP server

```bash
python -m bsoccer.server      # stdio transport
# or, if installed: brazilian-soccer-mcp
```

Example MCP client config (e.g. Claude Desktop `mcpServers`):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "python",
      "args": ["-m", "bsoccer.server"],
      "cwd": "/path/to/this/repo"
    }
  }
}
```

### Tools exposed

| Category | Tools |
|----------|-------|
| Matches | `find_matches` |
| Teams | `team_record`, `head_to_head` |
| Players | `search_players`, `players_by_club` |
| Competitions | `standings`, `champion`, `list_seasons` |
| Statistics | `competition_stats`, `biggest_wins`, `top_scoring_teams` |

Each tool returns `{ "text": <human-readable answer>, "data": <structured result> }`
so the connected LLM can quote the prose or reason over the fields.

## CLI (no MCP client needed)

```bash
python -m bsoccer.cli h2h Flamengo Fluminense
python -m bsoccer.cli standings --season 2019 --top 5
python -m bsoccer.cli record --team Corinthians --season 2022 --venue home
python -m bsoccer.cli players --nationality Brazil --min-overall 88
python -m bsoccer.cli stats --competition Brasileirão
python -m bsoccer.cli biggest --competition Brasileirão
```

Example output:

```
$ python -m bsoccer.cli standings --season 2019 --top 3
2019 Brasileirão Standings (calculated from matches):
1. Flamengo - 90 pts (28W, 6D, 4L) GF:86 GA:37
2. Palmeiras - 74 pts (21W, 11D, 6L) GF:61 GA:32
3. Santos - 74 pts (22W, 8D, 8L) GF:60 GA:33
```

## Sample questions the server can answer

1. Show me all Flamengo vs Fluminense matches → `find_matches(team, opponent)`
2. What matches did Palmeiras play in 2019? → `find_matches(team, season)`
3. Find Copa do Brasil matches → `find_matches(competition)`
4. What is Corinthians' home record in 2022? → `team_record(venue="home")`
5. Compare Palmeiras and Santos head-to-head → `head_to_head`
6. When did Flamengo last play Corinthians? → `find_matches` (sorted by date)
7. Who is Neymar / Gabriel Barbosa? → `search_players(name)`
8. Find all Brazilian players → `search_players(nationality="Brazil")`
9. Highest-rated players at a club → `search_players(club, sort_by="Overall")`
10. Show all forwards from a club → `search_players(club, position="ST,CF")`
11. Brazilian players grouped by club → `players_by_club`
12. Who won the 2019 Brasileirão? → `champion`
13. 2019 final standings → `standings`
14. Which seasons/competitions exist? → `list_seasons`
15. Average goals per match in the Brasileirão → `competition_stats`
16. Home vs away win rates → `competition_stats`
17. Biggest wins in the dataset → `biggest_wins`
18. Which team scored the most goals in a season → `top_scoring_teams`
19. Best home record → `team_record(venue="home")` per team
20. Compare two seasons → `competition_stats` per season

## Tests

```bash
python -m pytest -q
```

47 tests covering normalization, data loading/dedup, every query category, the
MCP tools, and the formatters. The 2019 Brasileirão final table is used as a
known-truth anchor (Flamengo champions on 90 points).

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
