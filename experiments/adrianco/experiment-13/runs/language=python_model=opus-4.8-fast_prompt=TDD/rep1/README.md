# Brazilian Soccer MCP Server

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server that
exposes a knowledge-graph-style query interface over bundled Brazilian soccer
datasets (matches, competitions and FIFA players). An LLM client can call the
server's tools to answer natural-language questions about players, teams,
matches, competitions and statistics.

Built test-first (TDD) — see [`tests/`](tests/). The full specification is in
[`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md).

## What was built

| Module | Responsibility |
|--------|----------------|
| `brazilian_soccer/normalize.py` | Team-name normalization (strips state suffixes `-SP`, country tags `(URU)`, club-type tokens `FC`/`EC`/`Clube`, accents), multi-format date parsing, and goal parsing (`-` = unplayed). |
| `brazilian_soccer/data_loader.py` | Loads the 6 CSV files (each with its own schema) into uniform `Match` and `Player` records. |
| `brazilian_soccer/queries.py` | `KnowledgeGraph` query engine: match search, head-to-head, team records, player search, computed standings, and aggregate statistics. Also de-duplicates the overlapping source files. |
| `brazilian_soccer/server.py` | `SoccerService` (formats results as text) + FastMCP wiring exposing the tools. |
| `brazilian_soccer/demo.py` | Runs 22 sample questions against the bundled data. |

### MCP tools exposed

- `search_matches(team, team2, competition, season, limit)` — find matches by team(s), competition and/or season.
- `head_to_head(team_a, team_b, competition)` — win/draw record and recent meetings between two teams.
- `team_record(team, season, competition, venue)` — W/D/L, goals and win-rate; `venue` = `home`/`away`/`either`.
- `search_players(name, nationality, club, position, min_overall, limit)` — search FIFA players, sorted by Overall.
- `standings(competition, season, limit)` — league table computed from match results (3 pts win, 1 pt draw).
- `competition_champion(competition, season)` — season champion (top of the computed table).
- `statistics(competition, season)` — average goals/match, home-win rate, biggest wins.

## Installation

Requires Python 3.10+.

```bash
pip install -r requirements.txt      # installs `mcp` (and `pytest`)
# or, as an installable package with console scripts:
pip install -e .
```

## Running

### As an MCP server (stdio)

```bash
python -m brazilian_soccer          # or: brazilian-soccer-mcp
```

Register it with an MCP-capable client (e.g. Claude Desktop) — add to the
client's MCP server config:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "python",
      "args": ["-m", "brazilian_soccer"],
      "cwd": "/path/to/this/repo"
    }
  }
}
```

### Demo (no MCP client needed)

```bash
python -m brazilian_soccer.demo      # or: brazilian-soccer-demo
```

Prints answers to 22 sample questions ("Who won the 2019 Brasileirão?",
"Flamengo vs Fluminense head-to-head", "Top Brazilian players", etc.).

## Testing

```bash
python -m pytest
```

68 tests cover normalization, loading, the query engine (against small
fixtures with hand-verified expected values), the formatting/tool layer, and
smoke tests against the real datasets.

## Design notes

- **Team-name normalization.** The datasets name the same club many ways
  (`Palmeiras-SP`, `Palmeiras`, `Sociedade Esportiva Palmeiras`; `Cuiaba` vs
  `Cuiaba FC`; `Botafogo RJ` vs `Botafogo`). All matching is done via an
  accent/case-insensitive `team_key` that strips state suffixes, club-type
  tokens and known full names, so queries work regardless of the source's
  spelling.
- **Multiple formats.** ISO dates, Brazilian `DD/MM/YYYY` and datetime strings
  are all parsed; UTF-8 (`São`, `Grêmio`, `Avaí`) is preserved for display.
- **De-duplication.** The six files overlap heavily (the same Brasileirão
  fixture can appear in three files). `KnowledgeGraph` removes exact duplicates
  and collapses near-duplicates using two safe keys: *(competition, season,
  date, home team)* — a team plays once per day, so this merges name variants —
  and *(competition, season, ordered home/away pair)* — which merges copies
  that differ only by a ±1-day timezone offset. The played copy (with a score)
  is always preferred over an unplayed snapshot.

### Known limitations

Computed standings are **approximate**. Some source rows use genuinely
ambiguous abbreviations (a bare `Atletico` could be Atlético-MG, Atlético-GO or
Athletico-PR), which cannot be safely merged without risking the union of two
different clubs. As a result a season's table may contain a few extra "phantom"
teams or inflated game counts. Unambiguous queries — match search, head-to-head,
player lookups, and champion identification — are reliable (e.g. the 2019
Brasileirão champion is correctly reported as Flamengo).

## Data sources

Kaggle data can't be downloaded without an account, so these freely available
(with attribution) datasets are bundled under `data/kaggle/`:

| File | Source | License |
|------|--------|---------|
| `Brasileirao_Matches.csv` | [ricardomattos05/jogos-do-campeonato-brasileiro](https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro) | CC BY 4.0 |
| `Brazilian_Cup_Matches.csv` | (same) | CC BY 4.0 |
| `Libertadores_Matches.csv` | (same) | CC BY 4.0 |
| `BR-Football-Dataset.csv` | [cuecacuela/brazilian-football-matches](https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches) | CC0 Public Domain |
| `novo_campeonato_brasileiro.csv` | [macedojleo/campeonato-brasileiro-2003-a-2019](https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019) | CC BY 4.0 |
| `fifa_data.csv` | [youssefelbadry10/fifa-players-data](https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data) | Apache 2.0 |
