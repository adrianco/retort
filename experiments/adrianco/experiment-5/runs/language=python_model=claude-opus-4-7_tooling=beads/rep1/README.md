# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server that exposes a queryable knowledge
graph over six Kaggle Brazilian soccer datasets. The server lets any MCP-aware
LLM client answer natural language questions about players, teams, matches,
competitions, and statistics drawn from the provided CSV files — no external
network calls required.

## What's in the box

- `src/soccer_mcp/` — Python package
  - `data_loader.py` — UTF-8 tolerant CSV loader for all six datasets
  - `normalizer.py` — team-name normalisation that handles state suffixes
    (`Palmeiras-SP` vs `Palmeiras`), long forms (`Sport Club Corinthians
    Paulista` → `Corinthians`), and Atlético-MG vs Athletico-PR disambiguation
  - `queries.py` — pure-Python query layer (matches, teams, players,
    standings, statistics) returning JSON-friendly values
  - `server.py` — FastMCP server exposing 16 MCP tools and a
    `soccer://overview` resource
- `tests/` — BDD test suite written with `pytest-bdd`
  - `features/*.feature` — Gherkin specs for the five capability areas
  - `test_*_bdd.py` — Given/When/Then step definitions
  - `test_normalizer.py` / `test_server.py` — supporting unit/integration tests
- `data/kaggle/` — Six pre-downloaded Kaggle CSVs (see attribution below)
- `pyproject.toml` / `requirements*.txt` — installable package metadata

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[test]
```

## Running the MCP server

```bash
python -m soccer_mcp.server          # stdio MCP server, suitable for any MCP client
# or, after install:
brazilian-soccer-mcp
```

The corpus is loaded once at startup. By default the loader reads from
`data/kaggle/` inside the repo; override with `SOCCER_DATA_DIR=/path/to/csvs`.

## Running the tests

```bash
pytest
```

The suite parses every feature file, runs the matching step definitions
against the real corpus, and finishes in ~2 seconds.

```
tests/test_competitions_bdd.py ..
tests/test_matches_bdd.py ....
tests/test_normalizer.py .................
tests/test_players_bdd.py ....
tests/test_server.py ...
tests/test_statistics_bdd.py ....
tests/test_teams_bdd.py ...
37 passed
```

## Available MCP tools

| Tool | Purpose |
|---|---|
| `find_matches` | Filter matches by team, opponent, season, competition, dates, venue |
| `head_to_head` | Aggregated record + recent matches between two clubs |
| `team_record` | W/D/L/goals for a team, optionally home- or away-only |
| `compare_teams` | Side-by-side records plus head-to-head |
| `find_players` | FIFA player search by name / club / nationality / position / overall |
| `top_brazilian_players` | Highest-rated Brazilians in the FIFA dataset |
| `players_by_club` | Roster + average overall for a club |
| `competition_standings` | Season standings calculated from match results |
| `competition_summary` | Champion / top-3 / matches played for a season |
| `average_goals_per_match` | Mean goals + home/away/draw rates |
| `biggest_wins` | Matches with the largest goal-difference margin |
| `best_home_record` / `best_away_record` | Venue leaderboards |
| `overall_statistics` | Description of the loaded corpus |
| `list_competitions` / `list_seasons` | Metadata helpers |

A `soccer://overview` MCP resource returns the corpus description as JSON.

## Example MCP tool output

```jsonc
// competition_standings(season=2019, competition="Brasileirão")
[
  {"position": 1, "team": "Flamengo-RJ",  "points": 90, "wins": 28, "draws": 6,  "losses": 4,  "goal_difference": 49},
  {"position": 2, "team": "Palmeiras-SP", "points": 74, "wins": 21, "draws": 11, "losses": 6,  "goal_difference": 29},
  {"position": 3, "team": "Santos-SP",    "points": 74, "wins": 22, "draws": 8,  "losses": 8,  "goal_difference": 27},
  ...
]
```

```jsonc
// head_to_head(team_a="Flamengo", team_b="Fluminense")
{
  "matches_played": 77,
  "team_a_wins": 31, "team_b_wins": 25, "draws": 21,
  "team_a_goals": 119, "team_b_goals": 102,
  "recent_matches": [/* most-recent-first */]
}
```

## Implementation notes

- **No third-party runtime dependencies beyond MCP.** The query layer uses
  only the Python standard library (`csv`, `dataclasses`, `datetime`,
  `collections`) so the package starts quickly and the smoke test reads all
  ~24 000 match rows + 18 000 player rows in well under a second.
- **Team-name normalisation** keeps state suffixes when they appear, so
  `Atletico-MG` and `Atletico-PR` are not collapsed onto the same key. A
  hand-curated alias map handles long-form names (`SE Palmeiras`,
  `Sport Club Corinthians Paulista`).
- **Cross-dataset matching** is done via substring matching with a minimum
  base length of 4, so `Palmeiras` correctly merges with `Palmeiras-SP` while
  short stubs like `fla` do not accidentally match `Flamengo`.

## Data Sources

Kaggle data can't be downloaded without an account, so these (freely
available with attribution) data sets have been downloaded for use here:

- https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro — CC BY 4.0
  - `data/kaggle/Brasileirao_Matches.csv`
  - `data/kaggle/Brazilian_Cup_Matches.csv`
  - `data/kaggle/Libertadores_Matches.csv`
- https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches — CC0
  - `data/kaggle/BR-Football-Dataset.csv`
- https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019 — CC BY 4.0
  - `data/kaggle/novo_campeonato_brasileiro.csv`
- https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data — Apache 2.0
  - `data/kaggle/fifa_data.csv`

The FIFA dataset is from the FIFA 19 / FIFA 20 era. EA did not hold the CBF
licence at that time, so Flamengo, Palmeiras, and São Paulo are absent from
`fifa_data.csv` while Cruzeiro, Santos, Internacional, Grêmio, Atlético
Mineiro and others are present. Player queries reflect that.
