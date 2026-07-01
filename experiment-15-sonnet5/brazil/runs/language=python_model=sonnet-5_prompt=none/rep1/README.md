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

A Python MCP server implementing the spec lives in `soccer_mcp/`:

- `team_names.py` — normalizes team names across datasets (state/country
  suffixes, accents, parenthetical qualifiers, club rebrands like
  Atletico/Athletico Paranaense) into a stable canonical key, without
  merging distinct clubs that merely share a short name (e.g. Botafogo-RJ
  vs Botafogo-PB, or Guarani-SP vs Club Guaraní of Paraguay).
- `data_loader.py` — loads and parses all six CSVs into unified `Match`/
  `Player` records. Brasileirao_Matches.csv, novo_campeonato_brasileiro.csv
  and the "Serie A" rows of BR-Football-Dataset.csv (and similarly
  Brazilian_Cup_Matches.csv vs. the "Copa do Brasil" rows) describe the same
  real-world matches for overlapping seasons; a dedup pass keeps one
  authoritative source per season so aggregate stats aren't double- or
  triple-counted.
- `repository.py` — the query engine: match search, head-to-head, team
  records, calculated league standings, biggest wins, goal averages, and
  player search/ranking.
- `server.py` — exposes the repository as MCP tools over stdio via the
  official `mcp` Python SDK (`FastMCP`).

### Running

```
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m soccer_mcp.server   # runs the MCP server over stdio
pytest                        # run the test suite
```
