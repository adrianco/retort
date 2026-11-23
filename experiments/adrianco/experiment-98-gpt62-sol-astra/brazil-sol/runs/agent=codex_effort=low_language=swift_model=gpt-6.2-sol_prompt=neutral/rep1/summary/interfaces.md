# Interfaces

## Transport

JSON-RPC 2.0 over stdio (newline-delimited). Methods: `initialize` (negotiates protocolVersion, advertises `tools`), `ping`, `tools/list`, `tools/call`. Unknown methods → `-32601`; parse errors → `-32700`; bad params → `-32602`. Notifications (no `id`) return no response.

## CLI

| Command | Flags | Behaviour |
|---------|-------|-----------|
| `soccer-mcp` | `--data-dir <path>` (default `data/kaggle`), `--help` | Load datasets, serve JSON-RPC on stdio |

## MCP tools (`tools/call`)

| Tool | Key args | Returns |
|------|----------|---------|
| `search_matches` | team, opponent, venue, competition, season, from, through, round, stage, source, derbiesOnly, limit, offset | Paged matches (R3/R4/R5/R11) |
| `team_record` | team*, opponent, venue, competition, season, includePlayers, limit | W/L/D, goals for/against, points, win rate; byVenue/byCompetition/bySeason; optional FIFA roster join (R6/R11) |
| `search_players` | name, club, nationality, position, domesticClubsOnly, groupByClub, limit, offset | FIFA players with overall + attributes, optional club aggregates (R7/R8) |
| `competition_season` | competition*, season*, mode (standings/champion/relegation/bracket/schedule/results/top_scorers) | Standings computed from matches, cup brackets, champions (R9) |
| `analyze_matches` | mode (summary/rank_teams/biggest_wins), seasons, rankVenue, sort, minimumMatches | goalsPerMatch, home/away win rates, team rankings, biggest wins (R10) |
| `data_coverage` | — | Per-source row counts, merged fixture count, competitions |

`*` = required arg.

## Data schema

`Match`: id, date?, kickoff?, home, away, competition, season?, round?, stage?, homeGoals?, awayGoals?, stadium?, details, sources[]. `Player`: id, name, club?, nationality, overall, position?, attributes, source. Both `Encodable`; responses are JSON objects, large lists paged via `total`/`offset`/`nextOffset`.

Datasets consumed from `data/kaggle/`: `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`, `novo_campeonato_brasileiro.csv`, `BR-Football-Dataset.csv`, `fifa_data.csv`.
