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

A Python MCP server (`mcp` SDK 2.x, `MCPServer`) that loads all six CSV files into an
in-memory knowledge base and exposes 17 query tools. No database is needed; loading takes about 0.5 s
and every query finishes in milliseconds.

| File | Purpose |
|------|---------|
| `team_names.py` | Team-name normalization (accents, state suffixes, aliases, full names), FIFA club mapping, derby list |
| `data_loader.py` | CSV loading, date parsing, cross-file de-duplication, cup-stage labelling, FIFA players |
| `queries.py` | Query engine: matches, head-to-head, records, standings, rankings, statistics, cups, derbies, players |
| `server.py` | MCP server exposing the query engine as tools (stdio or streamable HTTP) |
| `tests/` | 182 pytest tests, including 27 sample questions answered through the MCP protocol |

### Running

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python -m pytest              # run the tests
python server.py              # MCP over stdio
python server.py --http 8000  # MCP over streamable HTTP
```

Claude Desktop / Claude Code config:

```json
{"mcpServers": {"brazilian-soccer": {"command": "/path/to/venv/bin/python", "args": ["/path/to/server.py"]}}}
```

### Tools

| Tool | Answers questions like |
|------|------------------------|
| `search_matches` | "What matches did Palmeiras play in 2023?", "When did Flamengo last play Corinthians?" (team, opponent, competition, season, date range, home/away, cup stage) |
| `head_to_head` | "Compare Palmeiras and Santos head-to-head" |
| `team_record` | "What is Corinthians' home record in 2022?" |
| `team_overview` | "What competitions has Palmeiras played in?" (match data + FIFA squad together) |
| `team_trend` | League position and points season by season |
| `standings` | "Who won the 2019 Brasileirão?", "Which teams were relegated in 2020?" |
| `team_rankings` | "Which team scored the most goals in 2023?", "Which team has the best away record?" |
| `competition_stats` | "What's the average goals per match in the Brasileirão?" |
| `compare_seasons` | "Compare the 2018 and 2019 seasons" |
| `biggest_wins` | "Show me the biggest wins in the dataset" |
| `knockout_results` | "Find all Copa do Brasil finals", "Show the 2018 Libertadores bracket" |
| `derby_matches` | "Show me all derbies in 2023" (Fla-Flu, Grenal, Derby Paulista, …) |
| `search_players` | "Find all Brazilian players", "Show me all forwards from Santos" |
| `player_profile` | "Who is Neymar?" (linked to the club's match record when the club is Brazilian) |
| `player_club_summary` | "Who are the top Brazilian players?" and player counts per club |
| `find_team`, `dataset_info` | Name lookup and dataset coverage |

### Data handling

- **Team names**: each spelling maps to one canonical id: `Palmeiras-SP`, `Palmeiras - SP`, `SE Palmeiras` →
  `palmeiras`; `Atlético-MG`, `Atletico Mineiro`, `Atlético - MG` → `atletico-mg`; `C. R. B. - AL` → `crb`.
  Clubs with the same name in a different state or country keep separate ids (Botafogo-PB, Flamengo-PI,
  Guaraní-PAR, Santos-AP).
- **De-duplication**: Série A matches for 2012-2019 are in three files. They are merged into one match.
  The priority order is `Brasileirao_Matches.csv` > `novo_campeonato_brasileiro.csv` > `BR-Football-Dataset.csv`.
  Lower-priority files add the arena and the corner/shot stats. The result is exactly 380 Série A matches
  per season for 2006-2022. 2022 is incomplete in the primary file, so the missing matches come from
  BR-Football. BR-Football rows labelled "Serie A" that match no known Série A game are dropped; these
  are mislabelled state-championship games.
- **Seasons**: the COVID-delayed 2020 season ran into early 2021. Those dated rows are assigned to 2020.
- **Dates**: ISO, ISO with time, and Brazilian `DD/MM/YYYY` are all accepted, both in the files and in tool
  arguments.
- **Cup stages**: Copa do Brasil round numbers are converted to final / semifinals / quarterfinals / round of 16.
  Finals for 2022-2023, which exist only in BR-Football, are inferred as the season's last two-legged tie.
- **Unplayed rows** (`NA` scores) are skipped.

### Known data limitations

- FIFA 19 includes only 15 Brazilian clubs. There are no Flamengo, Palmeiras, Corinthians or São Paulo squads,
  and the tools say so. Some players at Brazilian clubs have placeholder names.
- Standings are calculated from match results (3 points per win), so off-field point deductions are not
  applied. 2023 (BR-Football only) has 377 of 380 matches. Its table is marked as incomplete and uses
  "Leader" / "Relegation zone" instead of "Champion" / "Relegated".
- Penalty shoot-outs and the away-goals rule are not in the data. Ties that are level on aggregate are
  reported as such.
- In `BR-Football-Dataset.csv`, `ht_result`/`at_result` are actually the home and away team's full-time
  result (WON/LOST/DRAW), not half-time results.
- Top scorers can't be derived because no file has goal-scorer data.
