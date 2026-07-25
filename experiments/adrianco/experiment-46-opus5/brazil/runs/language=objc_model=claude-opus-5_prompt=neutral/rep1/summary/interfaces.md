# Interfaces

## HTTP routes

(none) — the server speaks MCP (JSON-RPC 2.0) over stdio, not HTTP.

## JSON-RPC / MCP methods

Handled by `BSMCPServer -handleMessage:` (dispatch at `BSMCPServer.m:115`):

| Method | Behaviour | Notes |
|--------|-----------|-------|
| `initialize` | Negotiates protocol version, returns server capabilities | Echoes client's requested version if supported, else newest supported |
| `notifications/initialized` | Marks server initialized; no reply | Notifications never answered |
| `ping` | Returns empty `{}` result | |
| `tools/list` | Returns `{tools: [...]}` — the 17 tool descriptors | |
| `tools/call` | Runs the named tool, returns text + `structuredContent` | Tool-level failures come back as `isError` results, not RPC errors |
| (any other) | Returns error `-32601` (method not found) | Malformed JSON → `-32700` |

## CLI commands

Entry point `main.m`:

| Invocation | Effect |
|-----------|--------|
| `brazilian-soccer-mcp [--data DIR]` | Serve MCP on stdio (default mode) |
| `brazilian-soccer-mcp [--data DIR] --list-tools` | Print the tool catalogue (name + title) |
| `brazilian-soccer-mcp [--data DIR] --call NAME '{json args}'` | Run one tool, print its answer, exit 0/1 |
| `--help` / `-h` | Usage |

`--data DIR` (or a bare positional path) points at the directory holding the six Kaggle CSV files; defaults to `../data/kaggle` searched upward from the executable, falling back to CWD.

## MCP tools (17)

Registered in `BSTools.m` (`-toolDefinitions`), dispatched in `-callTool:arguments:` (`BSTools.m:414`). Each returns human-readable `text` plus a complete `structuredContent` object.

| Tool | Title | Category |
|------|-------|----------|
| `search_matches` | Search matches | Match |
| `head_to_head` | Head-to-head record | Match/Team |
| `team_record` | Team record | Team |
| `team_profile` | Team profile | Team |
| `compare_teams` | Compare two teams | Team |
| `standings` | League table | Competition |
| `season_summary` | Season summary | Competition |
| `competition_info` | Competition coverage | Competition |
| `match_statistics` | Aggregate statistics | Stats |
| `biggest_wins` | Biggest victories | Stats |
| `team_rankings` | Team rankings | Stats |
| `find_derbies` | Find derbies | Match |
| `search_players` | Search players | Player |
| `player_profile` | Player profile | Player |
| `club_squad` | Club squad | Player |
| `list_teams` | List or resolve teams | Team |
| `dataset_info` | Dataset coverage | Meta |

Common arguments accepted (loosely coerced from LLM input): `team`, `opponent`/`team_a`/`team_b`, `competition`, `season`/`season_from`/`season_to`, `date_from`/`date_to`, `venue` (home/away/all), `round`/`stage`, `name`, `limit`, `query`.

## Data schema

In-memory graph nodes (no database):

- **BSClub** — canonical club node (base name + region, e.g. flamengo/RJ).
- **BSMatch** — a distinct fixture after cross-file merge: home/away clubs, goals, competition id, season, round/stage, date, optional stadium and extended stats (corners/shots/attacks).
- **BSPlayer** — FIFA player: name, age, nationality, overall/potential, club, position, skill ratings.

Source files consumed (from `data/kaggle/`): `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`, `BR-Football-Dataset.csv`, `novo_campeonato_brasileiro.csv`, `fifa_data.csv`.
