# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server that exposes a knowledge-graph-style
query interface over the six Kaggle Brazilian-soccer datasets shipped in
`data/kaggle/`.  Implemented in Python, stdlib-only at runtime aside from
the `mcp` package itself.

## What it does

The server loads every CSV at start-up, normalizes inconsistent
club/competition naming, deduplicates overlapping matches across data
sources, and surfaces a set of MCP tools that an LLM can call to answer
natural-language questions such as:

* "When did Flamengo last play Corinthians and what was the score?"
* "What is Corinthians' home record in the 2022 Brasileirão?"
* "Who won the 2019 Brasileirão?"
* "Show me the biggest wins in the dataset."
* "Find the highest-rated Brazilian players in the FIFA roster."

## Repository layout

```
brazilian_soccer_mcp/
    __init__.py        -- public package surface
    data_loader.py     -- stdlib CSV loaders + cross-file dedup
    team_utils.py      -- accent/state/alias normalization for club names
    queries.py         -- 5 capability groups (matches, teams, players,
                          competitions, statistics)
    server.py          -- MCP server (stdio) wiring the query layer
tests/
    conftest.py        -- session-scoped dataset fixture
    test_data_loading.py
    test_team_normalization.py
    test_match_queries.py
    test_team_queries.py
    test_player_queries.py
    test_competition_queries.py
    test_statistics.py
    test_mcp_server.py
data/kaggle/           -- the six provided CSV files (unchanged)
pyproject.toml         -- packaging metadata + entrypoint
TASK.md                -- specification driving this implementation
```

## Quick start

```bash
python3 -m venv .venv
.venv/bin/pip install -e .[dev]

# Run the test suite (63 BDD-style tests, ~1s total)
.venv/bin/pytest

# Run the MCP server over stdio (for connecting an MCP client / LLM)
.venv/bin/brazilian-soccer-mcp
```

A Claude / MCP-aware client configures the server with a stdio command:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": ".venv/bin/brazilian-soccer-mcp"
    }
  }
}
```

## Capabilities

Sixteen MCP tools, grouped by the five capability areas from the spec:

### 1. Match queries
* `find_matches(team?, opponent?, competition?, season?, date_from?, date_to?, home_only?, away_only?, limit?)`
* `head_to_head(team_a, team_b)`

### 2. Team queries
* `team_stats(team, season?, competition?, venue?)`
* `compare_teams(team_a, team_b, season?, competition?)`

### 3. Player queries
* `find_players(name?, nationality?, club?, position?, min_overall?, limit?)`
* `top_brazilian_players(limit?)`
* `brazilian_players_by_club(top_n_clubs?)`

### 4. Competition queries
* `competition_standings(competition, season)`  – computed league table from match results
* `champion(competition, season)`               – top of computed standings
* `list_seasons(competition?)`
* `list_competitions()`

### 5. Statistical analysis
* `biggest_wins(competition?, season?, limit?)`
* `overall_stats(competition?)`
* `best_home_record(competition?, season?, min_matches?, limit?)`
* `best_away_record(competition?, season?, min_matches?, limit?)`
* `top_scoring_teams(competition?, season?, limit?)`

All tool outputs are plain JSON-serializable dicts/lists.

## Data handling

### Team-name normalization (`team_utils.py`)

The datasets refer to the same club in several ways
("Palmeiras-SP", "Palmeiras", "Sociedade Esportiva Palmeiras"; "São Paulo"
vs. "Sao Paulo"; "Clube Atlético Mineiro" vs. "Atletico-MG").  Names are
canonicalized by:

1. Stripping accents and lowercasing.
2. Normalizing dashes / whitespace.
3. Looking up the full string in a state-aware alias table first
   (`atletico mg` → `atletico mineiro`, `atletico pr` → `athletico paranaense`),
   so the several "Atléticos" don't collide.
4. Falling back to a state-stripped lookup, then to a generic-token
   stripper for unknown clubs.

`Botafogo` and `Botafogo-PB` deliberately remain distinct because they
are different clubs in different states.

### Competition canonicalization

`Brasileirao_Matches.csv`, `novo_campeonato_brasileiro.csv`, and the
extended-stats `BR-Football-Dataset.csv` (which labels Série A as
"Serie A") all map onto the canonical name `"Brasileirão Série A"`.
Copa do Brasil and Copa Libertadores get matching canonical labels.

### Date parsing

`data_loader._parse_date` accepts ISO (`2023-09-24`), Brazilian
(`29/03/2003`), and full datetime (`2012-05-19 18:30:00`) formats.

### Deduplication across sources

The three Brasileirão datasets overlap heavily.  The loader treats two
matches as the same when they share `(competition, season, home_team,
away_team, scores)` and their dates are within four days – necessary
because BR-Football-Dataset stamps kickoff in UTC, often a day off from
the other sources.  After dedup, Flamengo's 2019 Brasileirão season
reduces to the expected 38 matches (28W 6D 4L, 90 points).

## Tests

63 BDD-style (Given/When/Then) tests covering:

| File                              | Scenarios                                  |
|-----------------------------------|--------------------------------------------|
| `test_data_loading.py`            | All six CSVs load, UTF-8 + date formats OK |
| `test_team_normalization.py`      | Aliases match, ambiguous clubs stay split  |
| `test_match_queries.py`           | Team/opponent/date/competition filters     |
| `test_team_queries.py`            | W/D/L/GF/GA invariants                     |
| `test_player_queries.py`          | Name / nationality / club / position       |
| `test_competition_queries.py`     | Standings, champion, season listing        |
| `test_statistics.py`              | Biggest wins, home/away records, totals    |
| `test_mcp_server.py`              | Tool registry + dispatcher round-trip      |

Run with `.venv/bin/pytest`.

## Data sources & licenses

| File                                  | Source (Kaggle)                                                      | License            |
|---------------------------------------|----------------------------------------------------------------------|--------------------|
| `Brasileirao_Matches.csv`             | ricardomattos05/jogos-do-campeonato-brasileiro                       | CC BY 4.0          |
| `Brazilian_Cup_Matches.csv`           | ricardomattos05/jogos-do-campeonato-brasileiro                       | CC BY 4.0          |
| `Libertadores_Matches.csv`            | ricardomattos05/jogos-do-campeonato-brasileiro                       | CC BY 4.0          |
| `BR-Football-Dataset.csv`             | cuecacuela/brazilian-football-matches                                | CC0                |
| `novo_campeonato_brasileiro.csv`      | macedojleo/campeonato-brasileiro-2003-a-2019                         | CC BY 4.0          |
| `fifa_data.csv`                       | youssefelbadry10/fifa-players-data                                   | Apache 2.0         |
