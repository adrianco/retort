# Brazilian Soccer MCP with spec and basic data sets

## Specification
brazilian-soccer-mcp-guide.md

## Implementation

An MCP server (`brazilian_soccer_mcp/`) built with the official Python `mcp` SDK
(`FastMCP`) and `pandas`, implementing `TASK.md`. Built test-first (pytest), 49
tests covering normalization, data loading, queries, and the MCP tool layer.

### Layout
- `brazilian_soccer_mcp/normalize.py` - canonicalizes team names (strips accents,
  punctuation, and state suffixes like "-SP"; keeps the state for the handful of
  genuinely ambiguous names such as "Atletico" and "America" that refer to
  different clubs in different states) and parses the dataset's mixed date formats.
- `brazilian_soccer_mcp/data_loader.py` - loads and unifies the 6 CSVs in
  `data/kaggle/` into one matches DataFrame and one players DataFrame. Seasons
  2012-2019 are covered by both `Brasileirao_Matches.csv` and
  `novo_campeonato_brasileiro.csv`; the latter is trimmed to its unique
  pre-2012 seasons so matches aren't double-counted in standings/records.
- `brazilian_soccer_mcp/queries.py` - pure functions for match search,
  head-to-head, team records, league standings (computed from results),
  biggest wins, average goals per match, home win rate, and player search/ranking.
- `brazilian_soccer_mcp/server.py` - wraps the query functions as MCP tools:
  `find_matches`, `head_to_head`, `team_record`, `standings`, `biggest_wins`,
  `average_goals_per_match`, `home_win_rate`, `search_players`, `top_players`.

### Running
```
pip install -r requirements.txt
python -m pytest                      # run the test suite
python -m brazilian_soccer_mcp.server # start the MCP server (stdio transport)
```

### Known limitations
- The FIFA player dataset (FIFA 19) does not license most Brazilian Série A
  clubs (e.g. Flamengo, Corinthians, Palmeiras are absent), so club-based
  player queries only return results for the clubs it does include
  (Cruzeiro, Fluminense, Bahia, Botafogo, Grêmio, Internacional, Santos, etc.).
- Team name normalization uses a curated alias list for common full legal
  names and the ~30 clubs with ambiguous shared nicknames; long-tail lower
  division club names (e.g. in `BR-Football-Dataset.csv`) normalize via the
  generic accent/punctuation/state-suffix rules only, without full aliasing.

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
