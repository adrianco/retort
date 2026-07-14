# Brazilian Soccer MCP Server

A Python [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server
that exposes the six bundled Kaggle datasets in `data/kaggle/` as natural-
language-queryable tools covering Brazilian club soccer: matches, teams,
players, competitions, and aggregate statistics.

The full specification lives in [TASK.md](TASK.md) (also mirrored in
`brazilian-soccer-mcp-guide.md`).

## Project layout

```
src/brazilian_soccer_mcp/
  normalize.py     # canonical team-name keys (handles "Palmeiras-SP" vs "Palmeiras")
  data_loader.py   # loads + dedupes all six CSVs into a single DataStore
  queries.py       # pure query functions over the DataStore
  server.py        # FastMCP server registering each query as an MCP tool
tests/             # pytest BDD-style tests (Given / When / Then)
scripts/smoke_mcp.py  # JSON-RPC stdio handshake against the installed server
```

## Install

```bash
python3 -m venv .venv
.venv/bin/pip install -e .[dev]
```

## Run the server

The server speaks MCP over stdio and is invoked via the installed console
script (suitable for use as an MCP client subprocess):

```bash
.venv/bin/brazilian-soccer-mcp
```

## Tools exposed

| Tool | Purpose |
|------|---------|
| `find_matches` | Search matches by team / competition / season / date range |
| `head_to_head` | Aggregate W/D/L and per-match list between two clubs |
| `team_stats` | W/D/L, GF/GA, points and win rate; filter by season / competition / venue |
| `team_competitions` | Competitions a club has appeared in, with counts and seasons |
| `find_players` | Search the FIFA player database by name / nationality / club / position |
| `top_brazilian_players` | Top FIFA-rated Brazilian players |
| `players_at_brazilian_clubs` | Group FIFA players by Brazilian club |
| `standings` | Compute a final season table from match results |
| `season_summary` | Champion, runner-up, last place, and full standings |
| `biggest_wins` | Largest-margin victories matching a filter |
| `aggregate_stats` | Average goals per match, home/away/draw rates |
| `top_scoring_teams` | Highest-scoring teams for a season+competition |
| `best_records` | Best home or away record for a season+competition |

## Data quality notes

- Team names are normalized to a canonical key that **preserves a 2-letter
  state suffix** (so `Atletico-MG` and `Athletico-PR` stay distinct) and
  collapses Portuguese boilerplate (`Clube de Regatas do Flamengo` →
  `flamengo`). A short-form lookup is used when the query doesn't specify a
  state, so `Palmeiras` still matches `Palmeiras-SP`.
- The overlapping Brasileirão sources (`Brasileirao_Matches.csv` 2012+,
  `novo_campeonato_brasileiro.csv` 2003-2019, and the BR-Football Serie A
  rows) are reduced to a single source per season so points tables are not
  double-counted.
- Dates from the Brazilian `DD/MM/YYYY` format are parsed alongside the ISO
  formats in the other files.

## Tests

```bash
PYTHONPATH=src .venv/bin/python -m pytest
```

44 BDD-style tests cover normalization, data loading, every query category,
and a live tool round-trip via the FastMCP adapter.

## End-to-end MCP smoke test

```bash
PATH="$PWD/.venv/bin:$PATH" .venv/bin/python scripts/smoke_mcp.py
# tools registered: 13
# standings rows: 20; champion: Flamengo-RJ (90 pts)
```

This script spawns the installed `brazilian-soccer-mcp` server, performs the
JSON-RPC `initialize` / `tools/list` / `tools/call(standings, season=2019)`
handshake, and prints a one-line summary confirming the server is alive.

## Data sources & licenses

The six bundled CSV files in `data/kaggle/` come from these freely-licensed
Kaggle datasets:

- [Brasileirão / Copa do Brasil / Libertadores match logs](https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro) — CC BY 4.0
  - `Brasileirao_Matches.csv`
  - `Brazilian_Cup_Matches.csv`
  - `Libertadores_Matches.csv`
- [Brazilian Football Matches (extended stats)](https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches) — CC0
  - `BR-Football-Dataset.csv`
- [Campeonato Brasileiro 2003-2019](https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019) — CC BY 4.0
  - `novo_campeonato_brasileiro.csv`
- [FIFA Players Data](https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data) — Apache 2.0
  - `fifa_data.csv`
