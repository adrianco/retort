# Brazilian Soccer MCP Server

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server that
exposes a knowledge-graph interface over a collection of Brazilian soccer
datasets, so an LLM can answer natural-language questions about players, teams,
matches and competitions.

Implemented in Python from the specification in
[`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md) /
[`TASK.md`](TASK.md).

## What was built

| Layer | Module | Responsibility |
|-------|--------|----------------|
| Normalization | `brazilian_soccer_mcp/normalization.py` | Team-name canonicalization, accent folding, multi-format date parsing, mixed int/float score parsing |
| Data loading | `brazilian_soccer_mcp/data_loader.py` | Loads all six CSV datasets into normalized `Match`/`Player` records; reconciles overlapping source files |
| Knowledge graph | `brazilian_soccer_mcp/knowledge_graph.py` | In-memory graph of Team / Player / Match / Competition nodes with team & club indexes |
| Query engine | `brazilian_soccer_mcp/queries.py` | High-level query API for the 5 capability categories + answer formatters |
| MCP server | `brazilian_soccer_mcp/server.py` | FastMCP server exposing 15 tools that return formatted answers |

The data and query layers depend **only on the Python standard library**; just
the MCP server itself imports the third-party `mcp` package (and that import is
isolated), so the whole package and its test suite import and run even without
`mcp` installed. The knowledge graph is held in memory rather than an external
graph database so the project builds and tests deterministically with no
services to provision; the full corpus (~16.6k deduplicated matches, ~18k
players) loads in ~0.5 s.

## Datasets used (`data/kaggle/`)

All six provided files are loaded and queryable:

| File | Competition | Notes |
|------|-------------|-------|
| `novo_campeonato_brasileiro.csv` | Brasileirão Série A | Historical 2003–2019 |
| `Brasileirao_Matches.csv` | Brasileirão Série A | 2012–2022 |
| `Brazilian_Cup_Matches.csv` | Copa do Brasil | |
| `Libertadores_Matches.csv` | Copa Libertadores | with stages |
| `BR-Football-Dataset.csv` | Brasileirão Série A/B/C, Copa do Brasil | extended stats; fills Série B/C and 2023 |
| `fifa_data.csv` | — | 18,207 FIFA players |

See dataset sources & licenses at the bottom of this file.

### Data-quality handling

The spec calls out several data-quality hazards, all of which are handled:

- **Team-name variations** — `Palmeiras-SP`, `América - MG`, `Nacional (URU)`,
  `Sport Club Corinthians Paulista` all collapse to one canonical key via
  suffix stripping, accent folding and an alias table.
- **Ambiguous base names** — `Atlético-MG`, `Atlético-GO` and `Athletico-PR`
  share the base "Atlético" but are kept **distinct** by their state suffix, so
  standings are not corrupted (e.g. the 2017 champion is correctly Corinthians,
  2021 correctly Atlético Mineiro).
- **Overlapping files** — the same season appears in up to three files. Each
  `(competition, season)` is sourced from a single authoritative file, so
  matches are never double-counted. This is validated against known history:
  the 2019 Brasileirão returns Flamengo as champion with exactly 90 points over
  38 games, and the correct four relegated clubs.
- **Date formats** — ISO, ISO+time and Brazilian `DD/MM/YYYY` are all parsed.
- **Encoding** — files are read as UTF-8 (with BOM tolerance) so accents and
  cedillas are preserved.

> Note: the bundled FIFA 19 dataset is licensed without a few big Brazilian
> clubs (Flamengo, Palmeiras, Corinthians), but does include many others
> (Santos, Grêmio, Fluminense, Internacional, …). Player-by-club queries work
> for clubs present in the data.

## MCP tools

`find_matches`, `last_match_between`, `team_record`, `head_to_head`,
`find_player`, `players_at_club`, `top_players`, `standings`, `champion`,
`relegated_teams`, `average_goals`, `biggest_wins`, `best_home_record`,
`best_away_record`, `list_competitions`.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt          # or: pip install -e ".[dev]"
```

## Running the server

```bash
python -m brazilian_soccer_mcp.server     # stdio transport
# or, once installed: brazilian-soccer-mcp
```

Register it with an MCP client (e.g. Claude Desktop) as an stdio server, for
example:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "python",
      "args": ["-m", "brazilian_soccer_mcp.server"]
    }
  }
}
```

## Testing (BDD / Given-When-Then with PyTest)

The suite is written in behavior-driven Given/When/Then style and covers every
capability category, the MCP server itself, and 24 representative sample
questions from the spec.

```bash
pytest
```

```
72 passed in ~1.3s
```

| Test file | Covers |
|-----------|--------|
| `tests/test_normalization.py` | Name/date/number normalization |
| `tests/test_data_loading.py` | Loading all 6 files, dedup, canonical competitions |
| `tests/test_match_queries.py` | Category 1 — match queries |
| `tests/test_team_queries.py` | Category 2 — team queries & head-to-head |
| `tests/test_player_queries.py` | Category 3 — player queries |
| `tests/test_competition_queries.py` | Category 4 — standings/champions/relegation (vs. known history) |
| `tests/test_statistics.py` | Category 5 — statistical analysis |
| `tests/test_mcp_server.py` | MCP tool registration & invocation |
| `tests/test_sample_questions.py` | ≥ 20 answerable sample questions |

## Example results

```text
Brasileirão Série A 2019 champion: Flamengo (90 pts, 28W 6D 4L)
1. Atlético Mineiro - 84 pts (26W, 6D, 6L) GD +33      # 2021 standings leader
Flamengo vs Fluminense — head-to-head across the data with W/D/L tally
```

## Project layout

```
brazilian_soccer_mcp/      # package
  normalization.py
  data_loader.py
  knowledge_graph.py
  queries.py
  server.py
tests/                     # BDD GWT pytest suite
data/kaggle/               # provided CSV datasets
pyproject.toml             # packaging + pytest config
requirements.txt
```

## Data Sources

Kaggle data can't be downloaded without an account, so these freely available
(with attribution) datasets were pre-downloaded into `data/kaggle/`:

- https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro
  — License: CC BY 4.0
  (`Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`)
- https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches
  — License: CC0 Public Domain (`BR-Football-Dataset.csv`)
- https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019
  — License: CC BY 4.0 (`novo_campeonato_brasileiro.csv`)
- https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data
  — License: Apache 2.0 (`fifa_data.csv`)

Use case: demo / non-commercial.
