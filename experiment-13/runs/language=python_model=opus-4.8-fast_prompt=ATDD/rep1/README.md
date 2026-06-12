# Brazilian Soccer MCP Server

An [MCP](https://modelcontextprotocol.io) server that answers natural-language
questions about Brazilian soccer — matches, teams, players, competitions and
aggregate statistics — over the pre-downloaded Kaggle datasets in
`data/kaggle/`. It implements the specification in
[`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md) /
[`TASK.md`](TASK.md).

## What it does

The server loads the six provided CSV files into an in-memory knowledge base and
exposes six MCP tools, one per capability category in the spec:

| Tool | Capability | Example question |
|------|-----------|------------------|
| `find_matches` | Match queries (by team, opponent, competition, season, date range, home/away) | "Show me all Flamengo vs Fluminense matches" |
| `get_team_record` | Team win/draw/loss record, goals, win rate | "What is Corinthians' home record in 2022?" |
| `head_to_head` | Head-to-head between two teams | "Compare Palmeiras and Santos head-to-head" |
| `search_players` | Player search by name, nationality, club, position, rating | "Who are the highest-rated players at Santos?" |
| `get_standings` | League table calculated from match results | "Who won the 2019 Brasileirão?" |
| `get_competition_stats` | Goals/match, home & away win rates, biggest wins | "What's the average goals per match in the Brasileirão?" |

When `find_matches` is given two teams it also returns a head-to-head summary, so
questions like "Show me all Flamengo vs Fluminense matches" come back with both
the fixtures and the win tally.

## Architecture

```
brazilian_soccer_mcp/
  normalize.py        team / text normalization (state & country suffixes,
                      accents, club aliases, ambiguous multi-state clubs)
  models.py           Match and Player domain records
  loader.py           parse the six CSV schemas into domain records
  knowledge_base.py   the query engine (find / record / h2h / players /
                      standings / stats)
  server.py           the FastMCP tool surface + stdio entry point
```

The server is intentionally dependency-light (standard-library `csv`, no pandas)
and loads all data once at start-up.

### Data-quality handling

The spec calls out several data-quality issues, all handled in `normalize.py`
and `loader.py`:

- **Team name variations** — `Palmeiras-SP`, `Nacional (URU)`,
  `Sport Club Corinthians Paulista` and `Palmeiras` all resolve to a single
  canonical name, and queries match regardless of suffixes or accents
  (`Sao Paulo` finds `São Paulo`). Clubs that genuinely differ only by state
  (`Atlético-MG` vs `Atlético-PR`) keep their state so they are not merged.
- **Multiple date formats** — ISO (`2023-09-24`), with time
  (`2012-05-19 18:30:00`) and Brazilian `DD/MM/YYYY` (`29/03/2003`) are all
  parsed to ISO dates.
- **UTF-8 / BOM** — files are read as `utf-8-sig`; the FIFA file's leading BOM
  column is handled transparently.
- **Overlapping sources** — the same competition appears in several files (the
  Brasileirão Série A is in three of them) under different spellings. For each
  competition-season the single richest source file is used, so standings and
  records stay internally consistent and are not double-counted. Verified
  against reality: e.g. the 2019 Brasileirão returns Flamengo as champion with
  90 points from 38 matches across 20 teams.

## Running the server

Install and launch over stdio (the transport MCP clients use):

```bash
pip install -r requirements.txt        # or: pip install -e .
python -m brazilian_soccer_mcp.server  # serves data/kaggle by default
```

Point it at a different data directory with `BRZ_SOCCER_DATA_DIR`. An installed
console script `brazilian-soccer-mcp` is also provided.

Example MCP client configuration:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "python",
      "args": ["-m", "brazilian_soccer_mcp.server"],
      "env": { "BRZ_SOCCER_DATA_DIR": "data/kaggle" }
    }
  }
}
```

## Development — ATDD

The system was built test-first following executable Acceptance Test-Driven
Development. Each requirement in the spec is an automated acceptance scenario in
[`tests/test_acceptance.py`](tests/test_acceptance.py) that exercises the server
**only through the MCP protocol** (tools invoked by name over an in-memory
client/server session), seeds its own small controlled dataset, and asserts on
domain outcomes ("find matches between two teams", "calculate the standings")
rather than implementation details. Finer-grained unit tests
([`tests/test_unit.py`](tests/test_unit.py)) cover the internals, and
[`tests/test_real_data.py`](tests/test_real_data.py) checks the real datasets all
load and answer end-to-end.

```bash
pip install -r requirements.txt
pytest -q
```

## Data Sources

Kaggle data can't be downloaded without an account, so these (freely available
with attribution) datasets have been downloaded for use here:

https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro
— License: Attribution 4.0 International (CC BY 4.0)
- `data/kaggle/Brasileirao_Matches.csv`
- `data/kaggle/Brazilian_Cup_Matches.csv`
- `data/kaggle/Libertadores_Matches.csv`

https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches
— License: CC0: Public Domain
- `data/kaggle/BR-Football-Dataset.csv`

https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019
— License: Attribution 4.0 International (CC BY 4.0)
- `data/kaggle/novo_campeonato_brasileiro.csv`

https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data
— License: Apache 2.0
- `data/kaggle/fifa_data.csv`
