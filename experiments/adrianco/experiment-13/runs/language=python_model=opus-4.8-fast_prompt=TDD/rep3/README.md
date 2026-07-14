# Brazilian Soccer MCP Server

An [MCP](https://modelcontextprotocol.io) server that exposes a queryable
knowledge base over Brazilian soccer datasets (Brasileirão Série A/B/C, Copa do
Brasil, Copa Libertadores matches, and FIFA player attributes). An LLM client
connects to it and answers natural-language questions about players, teams,
matches, competitions, and statistics.

Built test-first (TDD) in Python. See [`TASK.md`](TASK.md) for the full
specification.

## What was built

```
brazilian_soccer/
  normalize.py        Team-name / date normalization (the matching foundation)
  data_loader.py      Load all 6 CSVs into a uniform Match / Player schema
  knowledge_base.py   SoccerKB: match search, records, standings, players, stats
  service.py          Format KB results into human-readable answers
  server.py           FastMCP server exposing 9 tools over stdio
tests/                98 unit + integration tests (pytest)
```

The layers are deliberately decoupled: all query/analytics and answer-formatting
logic is plain Python with no MCP dependency, so it is fully unit-tested. The
MCP server is a thin wrapper that loads the data once and delegates to the
`answer_*` formatters.

## Running the server

Install dependencies and launch the stdio MCP server:

```bash
pip install -r requirements.txt
python -m brazilian_soccer.server
```

The data directory defaults to `data/kaggle` and can be overridden with the
`BRAZILIAN_SOCCER_DATA_DIR` environment variable.

### Example MCP client config

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "python",
      "args": ["-m", "brazilian_soccer.server"],
      "env": { "BRAZILIAN_SOCCER_DATA_DIR": "/abs/path/to/data/kaggle" }
    }
  }
}
```

## Tools

| Tool | Purpose |
|------|---------|
| `find_matches` | Matches by team, opponent, competition, season, date range, venue |
| `head_to_head` | Win/draw/goal tally between two teams |
| `team_record` | A team's W/D/L, goals and win rate (optionally home/away) |
| `standings` | League table for a competition/season, computed from results |
| `search_players` | FIFA players by name, nationality, club, position, min rating |
| `competition_stats` | Matches, total/avg goals, home/away/draw rates |
| `biggest_wins` | Matches with the largest goal margins |
| `list_competitions` | Competitions available in the data |
| `list_seasons` | Seasons available (optionally per competition) |

## Example queries answered

- *"Who won the 2019 Brasileirão?"* → `standings("Brasileirão Série A", 2019)`
  ⇒ Flamengo, 90 pts (28W 6D 4L) — matches the official result.
- *"Show me all Flamengo vs Fluminense matches"* → `find_matches(team="Flamengo",
  opponent="Fluminense")` with a head-to-head summary.
- *"What is Corinthians' home record in 2017?"* → `team_record(... venue="home")`.
- *"Find all Brazilian players"* → `search_players(nationality="Brazil")`
  ⇒ 827 players, Neymar Jr (92) top-rated.
- *"What's the average goals per match in the Brasileirão?"* →
  `competition_stats(competition="Brasileirão Série A")`.

## Data handling decisions

The datasets are messy in exactly the ways TASK.md warns about, and the design
addresses each:

- **Team-name variations.** Names appear with state suffixes (`Flamengo-RJ`),
  country codes (`Nacional (URU)`), accents (`Grêmio`), and full official
  forms. `normalize.team_key` builds an accent-insensitive, tokenized key that
  **retains** the state suffix, so distinct clubs that share a base name
  (Atlético-**MG** vs Atlético-**PR**) never collide — while `names_match`
  stays loose enough that a bare `"Flamengo"` query still matches `Flamengo-RJ`.
- **Overlapping sources.** Série A appears in three files (2003-2019, 2012-2022,
  and 2014-2023) with off-by-one dates and divergent spellings, which defeats
  naïve per-row de-duplication. The loader instead selects **one authoritative
  source per `(competition, season)`** (file-priority order), falling back to
  lower-priority sources only for seasons the better ones don't cover. This is
  what makes computed standings exact (e.g. Flamengo's 38 games, not 58).
- **Date formats.** ISO dates/datetimes and Brazilian `DD/MM/YYYY` are all
  parsed to ISO `YYYY-MM-DD`.
- **Encoding.** All files are read as UTF-8 (BOM-tolerant) and accents are
  preserved in display while normalized for matching.

## Testing

```bash
python -m pytest          # 98 tests
```

Unit tests cover normalization, every CSV loader (including cross-source
de-duplication), the query/analytics layer, and answer formatting. Integration
tests run against the real datasets in `data/kaggle`, answer 20+ of the spec's
sample questions, and assert the data-coverage and performance criteria (load
< 5 s, simple lookup < 2 s).

## Data sources

Kaggle data can't be downloaded without an account, so these freely available
(with attribution) datasets were pre-downloaded into `data/kaggle/`:

- https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro
  — License: CC BY 4.0
  - `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`
- https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches
  — License: CC0 Public Domain
  - `BR-Football-Dataset.csv`
- https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019
  — License: CC BY 4.0
  - `novo_campeonato_brasileiro.csv`
- https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data
  — License: Apache 2.0
  - `fifa_data.csv`
