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

A dependency-free Python (3.10+) MCP server over the six CSV files.

```
brazilian_soccer/
  normalize.py   team-name, competition and date normalisation
  data.py        CSV loading, de-duplication of fixtures found in several files
  service.py     query layer (SoccerData): matches, teams, standings, stats, players
  server.py      MCP stdio server (JSON-RPC 2.0) and the tool definitions
tests/           pytest suite written as Given/When/Then scenarios
```

### Running

```bash
python -m brazilian_soccer.server        # MCP server on stdio
python -m pytest                         # tests (pytest is the only requirement)
```

Register it with an MCP client, e.g. for Claude Code:

```bash
claude mcp add brazilian-soccer -- python -m brazilian_soccer.server
```

(run from this directory, or set `cwd`/`PYTHONPATH` to it in the client configuration).

### Tools

| Tool | Answers |
|------|---------|
| `search_matches` | matches by team, opponent, competition, season, date range, venue, round/stage |
| `head_to_head` | record and match list between two teams |
| `team_stats` | W/D/L, goals, win rate; by season, competition, home/away |
| `team_competitions` | competitions and seasons a team appears in |
| `team_profile` | cross-file view: match record plus FIFA squad |
| `standings` | league table calculated from results |
| `season_summary` | champion, relegation zone, or cup final |
| `competition_stats` | goals per match, home/draw/away rates |
| `compare_seasons` | two seasons side by side |
| `rank_teams` | best home/away record, top attack, best defence, ... |
| `biggest_wins` | largest winning margins |
| `list_derbies` | matches between traditional rivals |
| `search_players` | FIFA players by name, nationality, club, position, rating, age |
| `player_details` | one player's full profile |
| `players_by_club` | squad size and average rating per club |
| `dataset_summary` | what is loaded |

### Data handling notes

- **Team names** are mapped to one canonical name per club ("Palmeiras-SP", "Palmeiras - SP",
  "Sociedade Esportiva Palmeiras" → `Palmeiras`), while clubs that merely share a name stay
  apart (`Atlético Mineiro` / `Atlético Goianiense`, `Botafogo` / `Botafogo-PB`).
- **Duplicates**: the same fixture often appears in up to three files. These are merged into
  one match (keeping round, stadium and extended statistics from each file), so the 23,954 CSV
  rows become 16,807 unique matches and statistics are not double counted.
- **Skipped rows**: fixtures without a score (`NA`/`-`), rows repeated within a file, and one
  mislabelled "Serie A" row played in January are ignored; `dataset_summary` reports the counts.
- **Seasons** for `BR-Football-Dataset.csv` (which has no season column) are taken from the
  date; matches in early 2021 belong to the pandemic-delayed 2020 season.
- **Cup finals**: the Copa do Brasil files do not label the final, so it is inferred as the
  last tie of each season. When a final is level on aggregate the winner is not guessed
  (penalties are not in the data), and a final missing from the data (Libertadores 2021, 2022)
  is reported as missing.
- **Known data limits**: the 2023 Serie A is three matches short; Serie C uses groups and
  play-offs, so its "standings" are an overall record; the FIFA file has no squads for
  Flamengo, Palmeiras, Corinthians, São Paulo or Vasco; the source file dates the 2020
  Libertadores final as 2020-01-30 (it was played in January 2021).
