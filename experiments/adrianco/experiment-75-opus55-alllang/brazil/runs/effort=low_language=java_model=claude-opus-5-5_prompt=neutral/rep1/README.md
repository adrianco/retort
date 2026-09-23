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

## Java MCP server (implementation)

Build and test: `mvn test`

Run as an MCP stdio server (from the repo root so `data/kaggle` resolves, or pass the data dir as arg / `SOCCER_DATA`):

```
mvn -q package -DskipTests && mvn -q dependency:build-classpath -Dmdep.outputFile=cp.txt
java -cp target/classes:$(cat cp.txt) soccer.McpServer data/kaggle
```

Tools: search_matches, last_match, head_to_head, team_stats, team_competitions, standings, champion,
relegated, finals, bracket, derbies, top_scoring_teams, competition_stats, biggest_wins, best_records,
compare_seasons, search_players, players_by_club, club_profile, dataset_info.
