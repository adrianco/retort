# Brazilian Soccer MCP with spec and basic data sets

## Specification
brazilian-soccer-mcp-guide.md

## Data Sources
Kaggle data can't be downloaded without an account so these (freely available with attribution) data sets have been downloaded for use here:

https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro
- License: Attribution 4.0 International (CC BY 4.0)
- data/kaggle/Brasileirao_Matches.csv
- data/kaggle/Brazilian_Cup_Matches.csv
- data/kaggle/Libertadores_Matches.csv

https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches
- License: CC0: Public Domain
- data/kaggle/BR-Football-Dataset.csv

https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019
- License: World Bank - Attribution 4.0 International (CC BY 4.0)
- data/kaggle/novo_campeonato_brasileiro.csv

https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data
- License: Apache 2.0
- data/kaggle/fifa_data.csv

## Implementation

An MCP server implementing the spec lives in `brazilian_soccer_mcp/`:

- `normalize.py` - team-name key normalization (accents, casing, state
  suffixes like "-SP", full legal names) and flexible date/goal parsing.
  Includes a known-club-state disambiguation step so, e.g., the famous
  Athletico Paranaense (many spellings: "Athletico-PR", "Atletico
  Paranaense", "Atlético-PR") all resolve to one team, while an unrelated
  lower-league club that happens to share a name with a famous one (e.g.
  "Flamengo-PI" vs. Rio's "Flamengo-RJ") stays distinct.
- `data_loader.py` - loads and normalizes all six CSVs into two unified
  pandas tables: `matches` (23,954 rows across five competitions/sources)
  and `players` (18,207 FIFA players).
- `graph.py` - an in-memory knowledge graph over those tables: team nodes
  (with their matches, competitions, states) and club rosters, for fast
  relationship lookups.
- `queries.py` - the query layer: match search, team records, head-to-head,
  standings/champions (calculated from match results, using one
  authoritative source per competition/season to avoid double-counting
  overlapping files), player search, and statistical analysis.
- `formatting.py` - turns query results into the human-readable text the
  MCP tools return.
- `server.py` - the MCP server itself (built on the official `mcp` Python
  SDK's FastMCP), exposing 14 tools covering match, team, player,
  competition and statistical queries.

### Running

```
pip install -r requirements.txt
python -m brazilian_soccer_mcp.server   # serves over stdio
```

### Testing

```
pip install -r requirements.txt
pytest
```

89 BDD-style tests (Given/When/Then) cover normalization, data loading,
the knowledge graph, the query layer (30+ scenarios drawn from TASK.md's
sample questions), the MCP tools end-to-end, and the query performance
budgets (<2s simple lookups, <5s aggregate queries). Notably, standings
calculated purely from the match data reproduce real-world results (e.g.
the 2019 Brasileirão: Flamengo champion, 90 points, 28W-6D-4L).

### Known data limitations

- The FIFA 2019 player dataset never licensed Flamengo, Palmeiras,
  Corinthians, São Paulo or Vasco da Gama (a real historical EA Sports
  gap), so `search_players`/`get_top_rated_players_at_club` return no
  roster for those clubs even though they're well represented in the
  match data.
- A handful of very obscure, identically-named lower-league clubs from
  different states may still collide under normalization; the
  disambiguation logic is tuned for the well-known clubs the sample
  questions in TASK.md ask about.
