# Brazilian Soccer MCP Server

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server that
provides a query interface over Brazilian soccer datasets — matches, teams,
competitions and FIFA player data. Connect it to an MCP-capable LLM client to
answer natural-language questions like *"Who won the 2019 Brasileirão?"* or
*"Compare Palmeiras and Santos head-to-head."*

The full specification is in [`TASK.md`](TASK.md) /
[`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md).

## What was built

A pure-Python MCP server (no external services or databases) that loads the
provided CSV datasets into memory at startup and exposes ten query tools over
the MCP protocol.

### Architecture

```
brazilian_soccer_mcp/
  normalize.py     # team-name / date / competition normalization
  models.py        # Match and Player domain models
  data_loader.py   # loads each CSV into the models (tolerant of bad rows)
  repository.py    # all query & aggregation logic (the domain layer)
  server.py        # FastMCP server: the 10 tools (the only public interface)
```

Design choices that address the data-quality notes in the spec:

- **Team-name normalization** — state/country suffixes (`Palmeiras-SP`,
  `América - MG`, `Barcelona-EQU`), parenthetical qualifiers (`Nacional (URU)`)
  and accents (`São Paulo` ≈ `Sao Paulo`, `Grêmio` ≈ `Gremio`) are folded to a
  common matching key so the same club matches across every file.
- **Multiple date formats** — ISO (`2023-09-24`), Brazilian (`29/03/2003`) and
  datetimes with a time component (`2012-05-19 18:30:00`) all parse.
- **UTF-8 / BOM** — files are read as `utf-8-sig`; accents are preserved in
  display names but folded for matching.
- **Cross-file de-duplication** — the datasets overlap (e.g. Brasileirão
  2012–2019 appears in two files). League fixtures are de-duplicated so a match
  is counted once. Because overlapping sources spell some teams differently,
  **standings are computed from the single most complete source per season** to
  keep each table internally consistent (the champion ordering matches the real
  historical results — 2017 Corinthians, 2018 Palmeiras, 2019 Flamengo).

### Tools (the public interface)

| Tool | Purpose |
|------|---------|
| `find_matches` | Matches by team, opponent, competition, season, date range, venue |
| `head_to_head` | Win/draw/goal totals between two teams |
| `team_record` | A team's W/D/L, goals and win rate (optionally by season/competition/venue) |
| `competition_standings` | League table for a season, calculated from match results |
| `competition_winner` | Champion of a competition/season |
| `competition_statistics` | Avg goals per match, home-win rate, totals |
| `biggest_wins` | Largest-margin victories |
| `search_players` | FIFA players by name, nationality, club, position or rating |
| `top_players` | Highest-rated players, optionally filtered |
| `list_competitions` | Competitions present in the data |

## Installation

```bash
pip install -e .          # installs the package and the `brazilian-soccer-mcp` script
```

Requires Python ≥ 3.10 and the `mcp` package (installed automatically).

## Running the server

The server speaks MCP over stdio. Point it at the data directory via the
`SOCCER_DATA_DIR` environment variable (defaults to `./data/kaggle`):

```bash
SOCCER_DATA_DIR=data/kaggle brazilian-soccer-mcp
# or:  python -m brazilian_soccer_mcp.server
```

Example MCP client configuration (e.g. Claude Desktop `mcpServers`):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "brazilian-soccer-mcp",
      "env": { "SOCCER_DATA_DIR": "/absolute/path/to/data/kaggle" }
    }
  }
}
```

## Development & testing

The project was built with **executable Acceptance Test-Driven Development**.
Every requirement in `TASK.md` is encoded as an automated acceptance test that
drives the server through the **real MCP protocol** (an in-memory
`ClientSession` calling tools) — there is no back-door access to internals.
Each test seeds its own isolated dataset, so the suite is atomic and order
independent.

```bash
pip install -e ".[dev]"
pytest
```

- `tests/acceptance/` — black-box tests per capability (match / team / player /
  competition / statistics queries, data-quality handling, server protocol).
- `tests/unit/` — finer-grained tests for normalization and the repository.

```
50 passed
```

## Data sources

The datasets in `data/kaggle/` are freely available with attribution:

- [jogos-do-campeonato-brasileiro](https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro)
  (CC BY 4.0) — `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`,
  `Libertadores_Matches.csv`
- [brazilian-football-matches](https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches)
  (CC0) — `BR-Football-Dataset.csv`
- [campeonato-brasileiro-2003-a-2019](https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019)
  (CC BY 4.0) — `novo_campeonato_brasileiro.csv`
- [fifa-players-data](https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data)
  (Apache 2.0) — `fifa_data.csv`

## Notes & limitations

- All six CSV files load and are queryable (~19,000 matches, ~18,000 players);
  startup parse is well under a second and queries respond in milliseconds.
- Historical match data is incomplete/inconsistent across sources for some
  seasons, so calculated point totals may differ slightly from official
  records, though champion and ordering are correct.
- Top scorers per competition are not derivable from the match data (no
  goalscorer detail) and are therefore not provided.
