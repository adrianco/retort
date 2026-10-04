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

## Implementation (Swift)

A dependency-free Swift package implementing the MCP server described in `TASK.md`.

- `Sources/BrazilianSoccer` — library: CSV reader, team-name normalisation, in-memory data store, queries, MCP tools and the JSON-RPC handler.
- `Sources/brazilian-soccer-mcp` — executable: MCP stdio transport (newline-delimited JSON-RPC 2.0).
- `Tests/BrazilianSoccerTests` — XCTest scenarios (Given/When/Then style) run against the real data.

```bash
swift build -c release
swift test
.build/release/brazilian-soccer-mcp            # finds ./data/kaggle; or --data-dir <path> / BRAZILIAN_SOCCER_DATA_DIR
```

Example MCP client configuration:

```json
{ "mcpServers": { "brazilian-soccer": {
    "command": "/path/to/.build/release/brazilian-soccer-mcp",
    "args": ["--data-dir", "/path/to/data/kaggle"] } } }
```

### Tools

| Tool | Answers |
|------|---------|
| `search_matches` | Matches by team, opponent, venue, competition, season, date range, stage/round |
| `head_to_head` | Two-team comparison: wins, draws, goals, home records, latest meeting |
| `team_stats` | W/D/L, goals, win rate; home/away, per-competition and per-season breakdowns |
| `team_profile` | Cross-file overview: competitions played plus the club's FIFA players |
| `league_standings` | Season table calculated from results (champion, relegation zone) |
| `knockout_bracket` | Libertadores / Copa do Brasil results by stage, with the final's winner |
| `competition_stats` | Goals per match, home/draw/away rates |
| `compare_seasons` | Side-by-side season summary |
| `biggest_wins` | Largest winning margins |
| `team_rankings` | Best home/away record, most goals, etc. |
| `find_derbies` | Matches between traditional rivals |
| `search_players` / `player_details` / `club_player_summary` | FIFA player search, profiles and per-club summaries |
| `dataset_summary` | Files, competitions and season coverage |

### Data handling notes

- Team names are split into a base name and state/country code, accent-folded and aliased, so
  "Palmeiras-SP", "Palmeiras - SP" and "Palmeiras" are one team while "Atlético-MG" / "Atlético-GO"
  and "Botafogo - RJ" / "Botafogo - SP" stay distinct.
- The same fixture often appears in several files; matches with the same competition, home and away
  team within two days are merged (keeping round, stadium and shot/corner statistics from each).
  Serie A merges cleanly (380 matches per season); some lower-division clubs in the Copa do Brasil
  are spelled too differently between files to merge, so a few cup ties are counted twice.
- Rows without a score (unplayed fixtures) are skipped. The 2023 Serie A data is missing a few
  matches, so that table is reported as provisional.
- The FIFA data has no Flamengo, Corinthians, Palmeiras or São Paulo squads.
