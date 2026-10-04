# Brazilian Soccer MCP Server (Go)

An [MCP](https://modelcontextprotocol.io) server that answers questions about Brazilian soccer (players, teams, matches, competitions) from the bundled Kaggle datasets. It is written in Go with no external dependencies. All six CSV files are loaded into an in-memory knowledge graph at startup (about 0.15 s), and every query runs in milliseconds.

The specification is in `TASK.md` (also `brazilian-soccer-mcp-guide.md`).

## Build, test, run

```bash
go build -o brazilian-soccer-mcp .
go test ./...                       # 60 tests against the real data
go test -bench . -run XXX           # aggregate query benchmark

./brazilian-soccer-mcp              # MCP server on stdio (logs go to stderr)
./brazilian-soccer-mcp -list        # list tools
./brazilian-soccer-mcp -tool standings -args '{"season":2019,"top":5}'   # CLI mode
```

The data directory is taken from `-data`, then `$BRAZIL_SOCCER_DATA`, then `./data/kaggle`, then `data/kaggle` next to the executable.

Register it with an MCP client, for example Claude Code:

```bash
claude mcp add brazilian-soccer -- /abs/path/brazilian-soccer-mcp -data /abs/path/data/kaggle
```

Or Claude Desktop (`claude_desktop_config.json`):

```json
{ "mcpServers": { "brazilian-soccer": {
    "command": "/abs/path/brazilian-soccer-mcp",
    "args": ["-data", "/abs/path/data/kaggle"] } } }
```

## Tools

| Tool | Answers questions like |
|------|------------------------|
| `search_matches` | "Show me all Flamengo vs Fluminense matches", "What matches did Palmeiras play in 2023?", "When did Flamengo last play Corinthians?" (filters: team, opponent, home/away, competition, season or season range, date range, cup stage) |
| `head_to_head` | "Compare Palmeiras and Santos head-to-head": W/D/L, goals, per-competition breakdown, recent meetings, biggest wins, derby name |
| `team_record` | "What is Corinthians' home record in 2022?": matches, W/D/L, goals, win rate, points, per-competition and per-season breakdowns |
| `team_overview` | "What competitions has Palmeiras played in?": competitions and seasons, Série A finishing positions, home/away split, rivals, FIFA squad (cross-file) |
| `standings` | "Who won the 2019 Brasileirão?", "Which teams were relegated in 2020?": table calculated from results (Série A/B/C) |
| `team_rankings` | "Which team scored the most goals in Serie A 2023?", "Which team has the best away record?" (metrics: points, wins, goals_for, goals_against, goal_difference, win_rate, points_rate, clean_sheets, goals_per_match, …) |
| `league_stats` | "What's the average goals per match in the Brasileirão?": goals/match, home/draw/away rates, common scorelines, corners/shots |
| `compare_seasons` | "Compare the 2018 and 2019 seasons" |
| `biggest_wins` | "Show me the biggest wins in the dataset" (by margin or total goals) |
| `knockout_matches` | "Find all Copa do Brasil finals", "Show the 2018 Copa Libertadores bracket": ties with aggregate scores by stage |
| `find_derbies` | "Show me all derbies in 2023" (Fla-Flu, Derby Paulista, Grenal, Clássico Mineiro, Ba-Vi, Atletiba, …) |
| `search_players` | "Find all Brazilian players", "Show me all forwards from Santos" (name, nationality or demonym, club, position code or group, min rating, max age) |
| `get_player` | "Who is Neymar?": full FIFA profile plus the club's record in the match data (cross-file) |
| `club_squads` | Brazilian clubs in FIFA 19 with player counts and average rating |
| `list_teams` | Shows how team names are normalised (canonical name, id, all spellings) |
| `dataset_info` | Files, rows, duplicates merged, coverage per competition |

Tool answers are plain text in the format shown in the spec (e.g. `2019-11-23: Flamengo 2-1 River Plate (Copa Libertadores 2019, final)`). Bad arguments come back as MCP tool errors (`isError: true`) with a helpful message. Protocol errors use JSON-RPC error codes.

## Design

| File | Contents |
|------|----------|
| `main.go` | Flags, data-dir discovery, stdio server / CLI mode |
| `mcp.go` | JSON-RPC 2.0 over newline-delimited stdio: `initialize` (version negotiation), `ping`, `tools/list`, `tools/call`, batches, notifications, panic recovery |
| `data.go` | CSV loaders for all 6 files, team registry, cross-file de-duplication, knowledge-graph nodes (`Team`, `Match`, `Player`) |
| `normalize.go` | Accent folding, team-name parsing and aliases, competition names, date formats |
| `queries.go` | Team resolution, match filtering, records, standings, derbies, player search |
| `tools.go` | MCP tool definitions (JSON Schemas) and answer formatting |

**Knowledge graph.** `Team` nodes link to their `Match` nodes (home/away edges). Each match carries competition, season, round/stage, score, stadium, extra statistics, and the source files it came from. A FIFA `Player` links to a `Team` when the player's club is a Brazilian club in the match data. Because of that link, a player profile can show the club's results, and a team overview can show its FIFA squad.

**Team-name normalisation.** Each raw name is accent-folded and its state or country suffix is parsed (`"Palmeiras-SP"`, `"Grêmio - RS"`, `"Nacional (URU)"`, `"Barcelona-EQU"`). Dotted acronyms are collapsed (`"C. R. B."` becomes `crb`), club-type words are dropped (`"Fortaleza EC"`, `"Paulista Futebol Clube"`), and aliases are applied (`"Athletico Paranaense"`, `"Atletico-PR"` and `"Athletico"` all map to `atletico-pr`; `"Sport Club Corinthians Paulista"` maps to `corinthians-sp`). A name with no state gets the state most often seen for that name, so `"Flamengo"` resolves to Flamengo-RJ and never to Flamengo-PI. In the Libertadores file, a name with no suffix is treated as Brazilian only if that club plays Série A, which keeps Argentina's River Plate separate from River Plate-SE. Queries accept any of these spellings.

**De-duplication.** Série A 2012–2019 appears in three files and 2012–2023 overlaps between two, so fixtures are merged across files: for leagues, same competition, season, home and away team; for cups, the same pair within 3 days. The highest-priority file supplies the score. BR-Football adds corners and shots, and fills in rows that another file marks as `NA`. This gives exactly 380 matches in every Série A season from 2006 to 2022.

**Dates and seasons.** The loader handles ISO dates, `DD/MM/YYYY`, and datetime values. BR-Football has no season column, so the season comes from the match date. The COVID-delayed 2020 season, played into early 2021, is assigned to 2020.

## Data-quality findings (handled in code)

- `novo_campeonato_brasileiro.csv` labels Vitória's state as `ES` instead of `BA`, so the state columns of that file are ignored.
- `novo_campeonato_brasileiro.csv` lists Botafogo vs Flamengo 2009 twice with the same home team. Repeated rows within one file are kept unless they are identical; this reproduces Flamengo's 2009 title at 67 pts.
- `BR-Football-Dataset.csv` repeats some fixtures one day apart (UTC vs local time). It also labels a regional Brasília FC vs CA Taguatinga game as Série A, which is dropped.
- `Brasileirao_Matches.csv` has 82 matches with `NA` scores. They are recovered from BR-Football where possible.
- Série A 2023 is missing 3 matches, so the computed table puts Grêmio ahead of the real champion, Palmeiras. `standings` prints a warning and labels rows "Leader in dataset" instead of "Champion".
- Copa do Brasil rounds are numbered. Stages are derived backwards from the final, and finals for seasons without round data (2021–2023) are inferred from the last tie. The 2022 Libertadores final has no score in the data.
- FIFA 19 has no player-likeness licence for Brazilian clubs, so their squads use generated names, and Flamengo, Palmeiras, Corinthians and São Paulo are absent. The tools say so.

## Tests

- `normalize_test.go`: accent folding, 30+ team-name spellings, competitions, date formats, stages.
- `store_test.go`: all 6 files load with the expected row counts. Name variants resolve to the same club and same-named clubs from other states stay separate. Each season has 380 fixtures after de-duplication. Champions are checked for 2003–2022, plus the 2019 table, 2020 relegations, Corinthians' 2022 home record, head-to-head symmetry, date/stage filters, player search and the FIFA-to-team links.
- `mcp_test.go`: handshake, tools/list schemas, tools/call success and error paths, batches, notifications, a full pipe round-trip, every tool with minimal arguments (each under 2 s), and argument validation.
- `questions_test.go`: 33 natural-language questions (all the spec examples plus more), each mapped to a tool call and checked for the expected facts.

## Data Sources

Kaggle data can't be downloaded without an account, so these data sets (freely available with attribution) have been downloaded for use here:

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
