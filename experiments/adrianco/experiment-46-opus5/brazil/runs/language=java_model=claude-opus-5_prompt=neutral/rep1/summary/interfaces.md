# Interfaces

## Transport

The project is an **MCP (Model Context Protocol) server over stdio** using the official
`io.modelcontextprotocol.sdk:mcp` Java SDK. `stdout` carries the JSON-RPC stream; all logs go to
`stderr`. Server identity: `brazilian-soccer-mcp` / "Brazilian Soccer Knowledge Graph" v1.0.0,
30-second request timeout, `tools` capability only. There are **no HTTP routes** — MCP is the only
network-facing surface.

## MCP tools (15)

| Tool | Title | Key arguments |
|------|-------|---------------|
| `dataset_info` | Dataset and graph overview | (none) |
| `search_matches` | Search matches | team, opponent, home_team, away_team, competition, season, season_from/to, date_from/to, round, venue, order, limit |
| `head_to_head` | Head-to-head record | team_a, team_b, competition, season, date_from/to |
| `find_derbies` | Find derbies | team |
| `team_stats` | Team statistics | team, competition, season, season_from/to, date range |
| `team_competitions` | Competitions of a club | team |
| `list_teams` | List clubs | query/filter |
| `standings` | Season table | competition, season |
| `competition_summary` | Competition season summary | competition, season |
| `compare_seasons` | Compare seasons | competition, season_from, season_to |
| `search_players` | Search players | name, nationality, club, position, min_overall, limit |
| `player_profile` | Player profile | name |
| `player_club_summary` | Players per club | club/competition filter |
| `player_club_report` | Player and club report | team |
| `statistics` | Aggregate statistics | metric (overview/biggest_wins/highest_scoring/team_ranking), competition, season(_from/to), team, venue, rank_by, min_matches, limit |

Every tool returns a single **plain-text content block** (human-readable answer, not JSON).
`ToolException` (unknown club, bad argument, missing season/competition) is returned as an MCP
error result so the model can self-correct; unexpected `RuntimeException`s are also returned as
error results rather than crashing the session.

## CLI (BrazilianSoccerMcpServer)

| Flag | Effect |
|------|--------|
| (no args) | Speak MCP over stdio |
| `--data, -d DIR` | Dataset directory (default `./data/kaggle` or `$BRAZIL_SOCCER_DATA_DIR`) |
| `--list-tools` | Print the tool catalogue and exit |
| `--call, -c NAME key=value ...` | Run one tool from the command line and print its text answer |
| `--help, -h` | Usage |

## Library API (transport-independent core)

- `DataLoader.load(Path) -> KnowledgeGraph`
- `new ToolRegistry(KnowledgeGraph)` — `.tools()`, `.tool(name)`, `.call(name, Map<String,Object>)`
- `McpServerFactory.createStdio(registry, in, out) -> McpSyncServer`
- `SoccerTool` record — `.name()`, `.title()`, `.description()`, `.inputSchema()`, `.call(args)`

## Data schema (in-memory graph)

Nodes and edges (materialised as adjacency indexes):

- **Team** (club): id, displayName, state, matchCount, playerCount
- **Match**: home/away team ids, home/away goals, season, competition, round/stage, optional
  `MatchStats` (corners, shots, attacks), source file(s)
- **Player** (FIFA): id, name, age, nationality, overall, potential, club, position, jersey,
  height/weight, skill ratings
- **Competition** (enum): `serie_a`, `serie_b`, `serie_c` (leagues), `copa_do_brasil`,
  `libertadores` (knockout)
- Edges: `(Team)-[HOME_TEAM|AWAY_TEAM]->(Match)`, `(Match)-[PART_OF]->(Competition)`,
  `(Player)-[PLAYS_FOR]->(Team)`

Source CSVs (loaded, de-duplicated and merged): `Brasileirao_Matches.csv`,
`Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`, `BR-Football-Dataset.csv`,
`novo_campeonato_brasileiro.csv`, `fifa_data.csv`.
