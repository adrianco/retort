# Brazilian Soccer MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) server that exposes a
knowledge-graph interface over Brazilian soccer datasets (Brasileirão, Copa do
Brasil, Copa Libertadores match data + the FIFA player database). It lets an LLM
answer natural-language questions about matches, teams, players, competitions and
statistics. See [`TASK.md`](TASK.md) for the full specification.

## What was built

| Layer | File | Responsibility |
|-------|------|----------------|
| Normalization | `brazilian_soccer_mcp/normalize.py` | Accent/suffix-aware team names, suffix-tolerant matching, multi-format date & score parsing |
| Domain model | `brazilian_soccer_mcp/models.py` | Immutable `Match` and `Player` value objects |
| Loaders | `brazilian_soccer_mcp/data_loader.py` | One parser per CSV schema → unified objects (stdlib `csv`, UTF-8) |
| Knowledge graph | `brazilian_soccer_mcp/knowledge_graph.py` | In-memory graph + all query logic (5 categories) |
| Formatting | `brazilian_soccer_mcp/formatting.py` | Renders results into the answer formats from the spec |
| MCP server | `brazilian_soccer_mcp/server.py` | 14 MCP tools over stdio (thin adapter over the graph) |
| Tests | `tests/` | BDD Given/When/Then PyTest suite (71 tests) + Gherkin feature file |
| Demo | `demo.py` | Answers 20+ sample questions with no MCP client required |

The data layer is **pure standard library** (no pandas/numpy), so it loads all
~37k rows in ~0.4s and runs anywhere. The only runtime dependency is the official
`mcp` SDK.

### Knowledge-graph model

```
Nodes : Team · Player · Competition · Season · Match
Edges : Team --played_in--> Match     Match --part_of--> Competition
        Player --plays_for--> Club     Player --nationality--> Country
```

Indexes (`team → matches`, `(competition, season) → matches`, `club → players`,
`nationality → players`) keep every query well inside the spec's 2s/5s budget.

## Key data-quality decisions

The datasets overlap and disagree (TASK.md "Data Quality Notes"). Two choices
were central to getting **correct** aggregates:

1. **The state/country suffix is identity, not noise.** `Atlético-MG`,
   `Atlético-GO` and `Atlético-PR` are *different clubs*. Team keys therefore
   keep the suffix (`atletico-mg`), while a user query like `"Palmeiras"` is
   resolved suffix-tolerantly to `Palmeiras-SP`, and `"Atlético"` (no suffix)
   matches the whole Atlético family.
2. **One authoritative source per `(competition, season)`.** The 2019 Brasileirão
   appears in *three* files. Merging them by fuzzy name match is unreliable, so
   for each competition/season the highest-priority source that covers it is used
   (e.g. `Brasileirao_Matches.csv` for 2012-2022, `novo_campeonato_brasileiro.csv`
   for 2003-2011, `BR-Football-Dataset.csv` for 2023). This prevents
   double-counting — a 20-team season correctly shows 38 games per club.

> **Note on the FIFA dataset:** it is FIFA-19 vintage and, due to club licensing,
> omits a few big Brazilian clubs (Flamengo, Palmeiras, Corinthians, São Paulo)
> while including most others (Fluminense, Santos, Grêmio, Cruzeiro, …). Player
> queries reflect exactly what the provided data contains.

## Installation

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt        # installs the `mcp` SDK + pytest
# or, to install as a package with the `bsoccer-mcp` console script:
pip install -e .
```

## Usage

### Try it without an MCP client

```bash
python demo.py
```

### Run the MCP server (stdio)

```bash
python -m brazilian_soccer_mcp.server      # or: bsoccer-mcp
```

### Register with Claude Desktop

Add to `claude_desktop_config.json` (adjust the path):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "python",
      "args": ["-m", "brazilian_soccer_mcp.server"],
      "cwd": "/path/to/this/repo"
    }
  }
}
```

The data directory is auto-discovered; override it with the
`BR_SOCCER_DATA_DIR` environment variable if needed.

## MCP tools

| Category | Tools |
|----------|-------|
| Match | `find_matches`, `head_to_head` |
| Team | `team_record`, `team_competitions` |
| Player | `search_players`, `get_player`, `players_by_club` |
| Competition | `standings`, `champion`, `list_competitions`, `list_seasons` |
| Statistics | `match_statistics`, `biggest_wins`, `best_record` |

Each tool accepts loose, human-friendly arguments (competition aliases like
"brasileirao"/"libertadores", suffix-optional team names, multiple date formats)
and returns a ready-to-read formatted answer.

## Example questions it answers

- *Show me all Flamengo vs Fluminense matches* → `find_matches`
- *What is Corinthians' home record in the 2022 Brasileirão?* → `team_record`
- *Compare Palmeiras and Santos head-to-head* → `head_to_head`
- *Who are the top Brazilian players?* → `search_players`
- *Who won the 2019 Brasileirão?* → `champion` / `standings`
- *What's the average goals per match in the Brasileirão?* → `match_statistics`
- *Show me the biggest wins in the dataset* → `biggest_wins`
- *Which team had the best away record in 2019?* → `best_record`

(See `demo.py` for 20+ worked examples across all five categories.)

## Testing

BDD-style (Given/When/Then) PyTest suite mirroring the Gherkin scenarios in
`tests/features/brazilian_soccer.feature`:

```bash
pytest                 # 71 tests, ~1.3s
```

Coverage includes: name/date normalization, all five query categories, the MCP
tool layer, dataset coverage (all 6 CSVs), and the de-duplication invariant
(no inflated round-robin seasons).

## Data sources

Kaggle data (downloaded, with attribution) under `data/kaggle/`:

| File | Source | License |
|------|--------|---------|
| `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv` | [ricardomattos05/jogos-do-campeonato-brasileiro](https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro) | CC BY 4.0 |
| `BR-Football-Dataset.csv` | [cuecacuela/brazilian-football-matches](https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches) | CC0 |
| `novo_campeonato_brasileiro.csv` | [macedojleo/campeonato-brasileiro-2003-a-2019](https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019) | CC BY 4.0 |
| `fifa_data.csv` | [youssefelbadry10/fifa-players-data](https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data) | Apache 2.0 |

Specification: [`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md) /
[`TASK.md`](TASK.md).
