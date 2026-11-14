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

A dependency-free Python MCP server (stdio, JSON-RPC 2.0) in `brazilian_soccer_mcp/`:

| File | Purpose |
|------|---------|
| `teams.py` | Team-name normalisation (state suffixes, accents, full names, aliases) |
| `data.py` | Loads the six CSV files (UTF-8, ISO and DD/MM/YYYY dates) |
| `queries.py` | `KnowledgeBase`: merges fixtures reported by several files, then answers match, team, player, competition and statistics queries |
| `server.py` | MCP protocol (`initialize`, `tools/list`, `tools/call`, `ping`) and text formatting |

### Run

```bash
python -m brazilian_soccer_mcp.server        # speaks MCP on stdin/stdout
python -m pytest                             # 119 tests, ~2 s
```

Register with an MCP client, e.g. Claude Code:

```bash
claude mcp add brazilian-soccer -- python -m brazilian_soccer_mcp.server
```

(run from this directory, or set `PYTHONPATH` to it). Python 3.10+; only `pytest` is needed, for the tests.

### Tools

| Tool | Answers |
|------|---------|
| `search_matches` | Matches by team, opponent, venue, competition, season, date range, stage (`stage="final"` for cup finals) |
| `head_to_head` | Record and matches between two teams |
| `team_stats` | W/D/L, goals and win rate, by season / competition / home-away |
| `team_profile` | Cross-file view: record per competition plus the club's FIFA players |
| `standings` | League table calculated from results, with champion and relegated teams |
| `competition_bracket` | A cup season grouped by stage |
| `competition_stats` | Goals per match, home/draw/away rates |
| `compare_seasons` | The same statistics for several seasons side by side |
| `rank_teams` | Best home/away record, most goals, fewest conceded, ... |
| `biggest_wins` | Largest winning margins |
| `derbies` | Matches between traditional rivals |
| `search_players` | FIFA players by name, nationality, club, position, rating |
| `player_details` | One player's full profile |
| `players_by_club` | Player count and average rating per club |
| `data_summary` | What is loaded |

### Data handling notes

- The same fixture often appears in up to three files. Duplicates are merged into one match
  (keeping round, stadium and corner/shot statistics from whichever file has them), leaving
  16,733 unique matches from 23,953 rows, so statistics are not double counted.
- Spellings of smaller clubs that differ between files ("AE Altos" / "Altos - PI") are learned
  from fixtures both files report. Clubs sharing a name in different states stay separate
  (Flamengo-RJ vs Flamengo-PI, Atlético-MG / -GO / -PR).
- Standings use 3 points per win, ordered by points, wins, goal difference, goals scored.
  Point deductions are not in the data. Champion/relegation labels appear only when a season
  is complete; 2023 is missing three matches, so it gets none.
- Not answerable from this data: individual goal scorers, and FIFA players for clubs absent
  from that dataset (Flamengo, Palmeiras, Corinthians, São Paulo, Vasco). The tools say so
  rather than guess.
