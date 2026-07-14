# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server that exposes the six Kaggle Brazilian
football datasets bundled in `data/kaggle/` as a queryable knowledge graph.
An LLM client can call its tools to answer natural-language questions about
matches, teams, players, competitions, and aggregate statistics.

The implementation follows the spec in [`TASK.md`](TASK.md) /
[`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md).

## What's here

```
src/brazilian_soccer_mcp/
  normalize.py     # collapse "Atlético-MG", "Galo", "Atletico Mineiro" -> one key
  data_loader.py   # load + dedup all five match CSVs and the FIFA player CSV
  queries.py       # pure query functions (match / team / player / competition / stats)
  server.py        # FastMCP server exposing 17 tools over stdio
tests/             # BDD-style pytest suite (56 tests, ~5s)
```

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[test]"
```

## Run the MCP server

```bash
.venv/bin/python -m brazilian_soccer_mcp.server
# or, after install:
.venv/bin/brazilian-soccer-mcp
```

The server speaks MCP over stdio. Wire it up in your MCP client (Claude
Desktop, etc.) by pointing the client at that command. Set
`BRAZILIAN_SOCCER_DATA_DIR` to use a CSV directory other than `data/kaggle/`.

## Run the tests

```bash
.venv/bin/pytest
```

## Tools exposed

| Category | Tool | What it does |
|---|---|---|
| Matches | `search_matches` | Filter by team / opponent / competition / season / date range |
| | `head_to_head` | Aggregate W/D/L between two clubs |
| | `last_match` | Most recent meeting of two clubs |
| Teams | `team_record` | W/D/L + goals for a team (optional home/away) |
| | `top_scoring_teams` | Goals-scored leaderboard |
| | `compare_teams` | Side-by-side comparison + head-to-head |
| Players | `search_players` | Filter FIFA roster by name / nationality / club / position / min rating |
| | `top_brazilian_players` | Top Brazilians by FIFA overall |
| | `brazilian_player_summary` | Brazilian-player counts per Brazilian club |
| Competitions | `season_standings` | Reconstructed league standings from match results |
| | `list_competitions` | Available competitions + match counts |
| | `list_seasons` | Available seasons (optional competition filter) |
| Statistics | `average_goals_per_match` | Mean goals per match in the filtered slice |
| | `biggest_wins` | Largest winning margins |
| | `home_away_split` | Home win / away win / draw rates |
| | `best_home_records` | Teams ranked by home win rate |
| | `best_away_records` | Teams ranked by away win rate |

Every tool returns a JSON-serializable dict.

## Datasets

The same six CSVs the spec describes, in `data/kaggle/`:

| File | Rows | Source |
|---|---|---|
| `Brasileirao_Matches.csv` | 4,180 | https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro |
| `Brazilian_Cup_Matches.csv` | 1,337 | (same as above) |
| `Libertadores_Matches.csv` | 1,255 | (same as above) |
| `BR-Football-Dataset.csv` | 10,296 | https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches |
| `novo_campeonato_brasileiro.csv` | 6,886 | https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019 |
| `fifa_data.csv` | 18,207 | https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data |

These five match files have heavy overlap (the historical Brasileirão CSV
covers 2003–2019, the modern Brasileirão CSV covers 2012–2023, and the
BR-Football CSV re-records many of the same fixtures in UTC). The data
loader deduplicates fixtures across sources using a two-pass key — exact
date + same fixture, then same month + same fixture — preferring the
"officially-shaped" Brasileirão / Cup / Libertadores files when a row
appears more than once. This is why the reconstructed 2019 Brasileirão
standings produce the real-world result (Flamengo champions with 90 points,
Santos and Palmeiras tied on 74).

## Implementation notes

- **Team-name normalization** is the load-bearing piece. The CSVs mix
  `Palmeiras` / `Palmeiras-SP`, `Atlético-MG` / `Atletico Mineiro`,
  `São Paulo` / `Sao Paulo`, plus Libertadores opponents tagged
  `Nacional (URU)`. `normalize.py` strips state and country suffixes,
  removes diacritics, and consults a small alias table to collapse every
  spelling to one canonical key. State-aware lookups distinguish
  `Atlético-MG`, `Atlético-PR`, and `Atlético-GO` (three different clubs
  sharing a base name).
- **Pure queries.** Every function in `queries.py` takes a `DataStore` and
  returns a JSON-able dict, so `server.py` is a thin wrapper that just
  registers the FastMCP tool decorators.
- **BDD tests.** `tests/` follows Given/When/Then structure with one class
  per scenario. The full suite exercises the real CSVs and runs in ~5
  seconds.

## License

Source code in this repository is MIT-licensed. The bundled CSVs retain
their original licences as listed in `TASK.md` (CC BY 4.0, CC0, Apache 2.0).
