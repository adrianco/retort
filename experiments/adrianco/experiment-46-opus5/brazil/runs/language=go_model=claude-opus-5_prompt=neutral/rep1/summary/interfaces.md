# Interfaces

The project is an MCP (Model Context Protocol) server over stdio, not an HTTP
service. Its "interface" is the set of MCP tools and resources it registers,
plus a small CLI wrapper for local invocation.

## HTTP routes

(none) — transport is MCP JSON-RPC over stdio (`mcp.StdioTransport`), or an
in-memory transport for the CLI paths.

## CLI commands

Single binary `brazilian-soccer-mcp` with flags (`main.go`):

| Flag | Effect |
|------|--------|
| (default) | Serve MCP over stdio |
| `-data <dir>` | Dataset directory (default: `$BRAZILIAN_SOCCER_DATA` or auto-discovered `data/kaggle`) |
| `-check` | Load datasets, print summary, exit (health check) |
| `-list-tools` | List MCP tool names + descriptions, exit |
| `-tool <name>` | Call one MCP tool via in-memory round trip and print its response |
| `-args <json>` | JSON arguments for `-tool` (default `{}`) |
| `-quiet` | Suppress start-up diagnostics on stderr |

## MCP tools

18 tools registered in `mcpserver/server.go` (`registerTools`), grouped by the
spec's five capability areas. Each returns a text block plus typed structured
content; the SDK derives the JSON schema from the Go arg struct.

| Tool | Purpose | Handler |
|------|---------|---------|
| `list_datasets` | Source datasets, row counts, licences, coverage | `listDatasets` |
| `graph_summary` | Node/edge counts, competitions, season coverage | `graphSummary` |
| `search_teams` | Find clubs by name/fragment (accents, suffixes, abbreviations) | `searchTeams` |
| `team_profile` | One club: identity, competitions/seasons, all-time record, FIFA squad | `teamProfile` |
| `team_stats` | W/D/L, goals, win rate; optional competition/season/venue scope | `teamStats` |
| `find_matches` | General match search: team, opponent, venue, competition, season, date range, stage | `findMatches` |
| `match_details` | Full detail for one match incl. shot/corner/attack stats | `matchDetails` |
| `head_to_head` | H2H record + meeting list, with derby name when applicable | `headToHead` |
| `competition_standings` | League table for a season, champion + relegation marked | `competitionStandings` |
| `list_competitions` | Competitions with seasons, match counts, club counts | `listCompetitions` |
| `competition_stats` | Goals/match, home advantage, clean sheets, biggest win, highest scoring | `competitionStats` |
| `team_leaderboard` | Rank clubs by points/wins/win rate/goals/GD; optional venue | `teamLeaderboard` |
| `notable_matches` | Biggest victories or highest-scoring matches | `notableMatches` |
| `compare_seasons` | Compare two seasons of a competition | `compareSeasons` |
| `find_derbies` | Matches between traditional rivals; optional club/competition/season scope | `findDerbies` |
| `search_players` | FIFA player search by name/nationality/club/position/rating/age | `searchPlayers` |
| `player_profile` | Full player profile: ratings, physicals, values, best skills | `playerProfile` |
| `club_squad` | FIFA squad for a club, linked to its match record | `clubSquad` |

## MCP resources

| URI | Name | MIME | Content |
|-----|------|------|---------|
| `brazilian-soccer://datasets` | datasets | application/json | Provenance/licence/coverage of the six Kaggle CSVs |
| `brazilian-soccer://graph` | graph | application/json | Node/edge counts, competitions, season coverage |

## Data schema (in-memory domain model, `model.go`)

- **Club**: ID, Name, State, Country, aliases; competitions/seasons appeared in.
- **Match**: home/away club IDs, home/away goals, competition, season, round,
  datetime, stage, stadium, sources, optional `ExtendedStats` (shots, corners,
  attacks, half-time results).
- **Player**: FIFA fields — ID, Name, Age, Nationality, Overall, Potential,
  Club, Position, jersey/physical attributes, skill ratings.
- **DatasetInfo**: file, rows, loaded, rejected, licence.

Data is loaded once from six CSVs in `data/kaggle/` (Brasileirão, historical
Brasileirão 2003–2019, Copa do Brasil, Libertadores, extended BR-Football stats,
FIFA players) into an in-memory graph; served read-only.
