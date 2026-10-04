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

A Python MCP server (`brsoccer/`) answers natural-language questions about Brazilian soccer.
It uses only the standard library: the MCP stdio transport (JSON-RPC 2.0) is implemented in
`brsoccer/server.py`, and the official MCP Python SDK client has been tested against it.

```
brsoccer/
  teams.py    team-name normalisation ("Palmeiras-SP" = "Palmeiras" = "Sociedade Esportiva Palmeiras")
  data.py     loads all 6 CSVs, parses dates, merges duplicate fixtures across files
  queries.py  query functions (matches, head-to-head, records, standings, brackets, stats, players)
  server.py   MCP server: tool definitions + JSON-RPC over stdio
  samples.py  28 sample questions mapped to tool calls
mcp_server.py entry point (same as `python -m brsoccer`)
demo.py       runs the sample questions without an LLM
tests/        pytest suite
```

### Running

```bash
python mcp_server.py          # MCP server on stdio (Python 3.10+, no dependencies)
python demo.py                # print answers to all sample questions
python -m pytest              # run the tests
```

Register it with an MCP client, e.g. Claude Code:

```bash
claude mcp add brazilian-soccer -- python /path/to/mcp_server.py
```

or Claude Desktop (`claude_desktop_config.json`):

```json
{"mcpServers": {"brazilian-soccer": {"command": "python", "args": ["/path/to/mcp_server.py"]}}}
```

Set `BRSOCCER_DATA_DIR` to read the CSVs from somewhere other than `data/kaggle/`.

### Tools

| Tool | Answers questions like |
|------|------------------------|
| `search_matches` | "Show me all Flamengo vs Fluminense matches", "What matches did Palmeiras play in 2023?", "When did Flamengo last play Corinthians?" (team, opponent, competition, season, date range, venue, stage) |
| `head_to_head` | "Compare Palmeiras and Santos head-to-head" (wins, goals, last meeting, biggest win, by competition, derby name) |
| `team_record` | "What is Corinthians' home record in 2022?" |
| `team_profile` | "What competitions has Palmeiras played in?" (seasons, record, titles worked out from the data, FIFA squad) |
| `standings` | "Who won the 2019 Brasileirão?", "Which teams were relegated in 2020?" |
| `knockout_bracket` | "Show the 2018 Copa Libertadores bracket" (aggregate scores per tie) |
| `finals` | "Find all Copa do Brasil finals" |
| `team_rankings` | "Which team has the best away record?", "Which team scored the most goals in Serie A 2023?" |
| `competition_stats` | "What's the average goals per match in the Brasileirão?" (plus home/draw/away rates, corners and shots) |
| `biggest_wins` | "Show me the biggest wins in the dataset" |
| `derbies` | "Show me all derbies in 2023" (Fla-Flu, Grenal, Derby Paulista, Choque-Rei, Majestoso, ...) |
| `compare_seasons` | "Compare the 2018 and 2019 seasons" |
| `search_players` | "Find all Brazilian players", "Show me all forwards from Santos" |
| `player_profile` | "Who is Neymar?" (suggests similar names when the player isn't in the data) |
| `club_players` | "Who are the highest-rated players at Grêmio?" (also shows the club's match record) |
| `brazilian_players_overview` | "Who are the top Brazilian players?" |
| `find_team`, `dataset_info` | how names resolve; what data is loaded |

Each tool returns formatted text in the style of the examples in the spec. Clients that negotiate
protocol `2025-06-18` also get the same answer as JSON in `structuredContent`.

### Data handling

* **One merged match list.** Série A 2012–2019 appears in three files, so the same match is merged into
  a single record keyed on (competition, season, home, away). The score comes from the
  highest-priority file; the arena comes from `novo_campeonato_brasileiro.csv` and the shots, corners
  and attacks come from `BR-Football-Dataset.csv`. As a result every Série A season from 2006 to 2022 has
  exactly 380 matches and 20 teams; the tests check this.
* **Team names.** State suffixes (`-SP`, ` - RJ`, ` RS`) and country tags (`(URU)`, `-PAR`) are
  stripped. Accents, punctuation and filler words (EC, FC, Clube) are ignored when matching names. A
  curated alias list covers the major clubs (Athletico/Atlético-PR, Vasco/Vasco da Gama, Sport/Sport
  Club do Recife, ...). Clubs from other states that share a famous name stay separate, e.g.
  `Flamengo (PI)` and `Botafogo (PB)`. For minor clubs spelled differently in BR-Football (e.g.
  "Brasil de Pelotas" vs "Brasil - RS"), the alias is learned by pairing fixtures that fall on the same
  date.
* **Dates.** ISO, ISO with time, and Brazilian `DD/MM/YYYY` dates are parsed. BR-Football kick-off
  times are in UTC and are converted to Brazilian local dates. Its 2020 season, which ran into early
  2021, is assigned to 2020.
* **Cup stages.** Copa do Brasil round numbers are mapped to Final, Semi-finals and so on by counting
  back from the final. For seasons that only appear in BR-Football, the final is inferred from the
  date order.
* **Known data limits.** The FIFA 19 database does not include Flamengo, Palmeiras, Corinthians, São
  Paulo or Vasco, and the tools say so when asked. Penalty shoot-outs are not in the data. Série A 2023
  has 377 of 380 matches. The 2022 Libertadores final row has no score. Standings are calculated purely
  from results, so they ignore points deductions.

### Tests

`python -m pytest`: 113 tests covering:
* name normalisation
* loading of all 6 files, including row counts, merging and UTF-8 handling
* query results checked against real-world facts, e.g. Flamengo's 2019 title with 90 pts
  (28W 6D 4L), the 2020 relegations, Copa do Brasil winners and River Plate's 2018 Libertadores win
* 28 sample questions sent through `tools/call`
* JSON-RPC protocol behaviour, including a real stdio subprocess
* performance: data loads in about 0.4 s, and queries take milliseconds against the 2 s and 5 s limits

`tests/test_sdk_interop.py` also drives the server with the official `mcp` SDK client. It runs when
`pip install mcp` has been done and is skipped otherwise.
