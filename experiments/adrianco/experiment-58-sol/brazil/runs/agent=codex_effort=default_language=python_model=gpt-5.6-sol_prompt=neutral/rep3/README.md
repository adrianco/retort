# Brazilian Soccer MCP Server

A read-only Model Context Protocol server over the six bundled Brazilian soccer datasets. It loads 23,854 scored matches and 18,207 FIFA player records, normalizes inconsistent team names and dates, and exposes exact match, player, standings, and statistical queries to an MCP-capable LLM.

The server uses the official MCP Python SDK and defaults to stdio transport. Data is loaded once on first use; typical in-process lookups take well under the specification's two-second limit.

## Install and run

Python 3.10 or newer is required.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
brazilian-soccer-mcp
```

An MCP client can launch it with this configuration:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/.venv/bin/brazilian-soccer-mcp",
      "args": []
    }
  }
}
```

For development, the equivalent direct command is:

```bash
python -m brazilian_soccer_mcp
```

By default the loader finds `data/kaggle` in the working repository. If the server is launched elsewhere, point it to the provided files with `BRAZILIAN_SOCCER_DATA_DIR=/absolute/path/to/data/kaggle`.

## MCP interface

The server provides a `soccer://datasets` resource and these tools:

| Tool | Purpose |
|---|---|
| `ask_soccer` | Route common natural-language demo questions to deterministic operations |
| `search_matches` | Filter by teams, season, competition, dates, home/away side, stage, or source |
| `team_statistics` | Wins/draws/losses, goals, points, and win rate |
| `head_to_head` | Two-team history and aggregate record |
| `search_players` | Filter FIFA players by name, nation, club, position, and rating |
| `standings` | Calculate a season table with standard Brazilian tie-break ordering |
| `competition_statistics` | Goal averages and home/away/draw rates |
| `biggest_victories` | Rank games by winning margin |
| `best_record` | Rank home or away performance with a minimum sample size |
| `team_competitions` | Traverse a team to competitions across match files |
| `derby_matches` | Find a curated set of traditional Brazilian rivalries |
| `competition_finals` | Find labeled finals or infer Copa do Brasil's highest round |
| `compare_seasons` | Compare scoring and results across seasons |
| `club_profile` | Join a team's match data with FIFA club/player records |
| `dataset_status` | Show usable and skipped row counts for all six sources |

Structured tools are preferable for exact work. `ask_soccer` supports the sample questions in the specification, but deliberately asks for clarification when a question such as “What was the score?” lacks teams or a date. It also states that top scorers cannot be inferred because the files contain team scores, not scorer events.

Example Python use without MCP transport:

```python
from brazilian_soccer_mcp import SoccerService

soccer = SoccerService()
print(soccer.head_to_head("Flamengo", "Fluminense"))
print(soccer.standings(2019))
print(soccer.search_players(nationality="Brazil", limit=10))
```

## Design and data quality

The package has four layers:

- `repository.py` parses every CSV into immutable `Match` and `Player` records.
- `normalize.py` handles UTF-8 accents, state suffixes, aliases, and three date formats. Ambiguous clubs such as Atlético Mineiro and Atlético Goianiense remain distinct.
- `service.py` performs deterministic graph-style traversal and aggregation.
- `query.py` routes recognized natural-language patterns; `server.py` publishes them through the official SDK's version-stable low-level MCP server API.

Some match files overlap. General searches deduplicate equivalent results but can query a specific raw `source`. Season tables and team-season records choose the most complete canonical source, using source priority to break ties. Rows without a final score (`NA`) remain accounted for in `dataset_status.skipped_rows` and are not treated as completed matches. Copa do Brasil is a knockout competition, so its highest numbered round can identify final legs, while a league-style table is explicitly labeled as non-authoritative for knockout champions.

The datasets are historical snapshots. The server does not provide live scores or current rosters, and optional external APIs are intentionally not required.

## Test

```bash
pytest
uv build --wheel
```

The 46 tests use Given/When/Then-style names and cover the MCP tool/resource contract, all six files, team normalization, multiple dates, match filters, complete-source selection, head-to-head records, standings, player attributes, cross-file club profiles, finals, derbies, aggregates, 20 natural-language questions, non-inferable facts, and the performance targets.

## Data sources and licenses

- `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, and `Libertadores_Matches.csv`: [Kaggle source](https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro), CC BY 4.0.
- `BR-Football-Dataset.csv`: [Kaggle source](https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches), CC0 Public Domain.
- `novo_campeonato_brasileiro.csv`: [Kaggle source](https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019), CC BY 4.0.
- `fifa_data.csv`: [Kaggle source](https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data), Apache 2.0.

See [TASK.md](TASK.md) for the complete benchmark specification.
