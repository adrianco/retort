# Brazilian Soccer MCP Server (C)

An MCP (Model Context Protocol) server, written in dependency-free C11, that answers
questions about Brazilian soccer from the six Kaggle datasets in `data/kaggle/`:
matches from the Brasileirão (Série A/B/C), Copa do Brasil and Copa Libertadores, plus
the FIFA player database. The specification is in `TASK.md` /
`brazilian-soccer-mcp-guide.md`.

## Build, test, run

```sh
make            # builds ./brsoccer-mcp
make test       # BDD scenarios (tests/test_bdd.c) + stdio end-to-end test
```

Requires only a C compiler and `make`. The server speaks newline-delimited JSON-RPC 2.0
on stdin/stdout (the MCP stdio transport) and loads all data into memory at start-up
(about 0.1 s; every query answers in milliseconds).

```sh
./brsoccer-mcp                                   # MCP server; data from ./data/kaggle
./brsoccer-mcp --data /path/to/data/kaggle       # or set BRSOCCER_DATA_DIR
./brsoccer-mcp --list                            # list the tools
./brsoccer-mcp --call standings '{"season":2019}'   # run one tool from the shell
```

Example MCP client configuration (use absolute paths):

```json
{ "mcpServers": { "brazilian-soccer": {
    "command": "/abs/path/brsoccer-mcp",
    "args": ["--data", "/abs/path/data/kaggle"] } } }
```

## Tools

| Tool | Answers questions like |
|------|------------------------|
| `search_matches` | "Show me all Flamengo vs Fluminense matches", "What matches did Palmeiras play in 2023?", "Find all Copa do Brasil finals", "When did Flamengo last play Corinthians?" |
| `head_to_head` | "Compare Palmeiras and Santos head-to-head" |
| `team_stats` | "What is Corinthians' home record in 2022?", "What competitions has Palmeiras played in?" |
| `standings` | "Who won the 2019 Brasileirão?", "Which teams were relegated in 2020?" |
| `team_rankings` | "Which team has the best away record?", "Which team scored the most goals in Serie A 2023?" |
| `competition_stats` | "What's the average goals per match in the Brasileirão?" |
| `compare_seasons` | "Compare the 2018 and 2019 seasons" |
| `biggest_wins` | "Show me the biggest wins in the dataset" |
| `competition_bracket` | "Show the 2018 Copa Libertadores bracket" |
| `derbies` | "Show me all derbies in 2023" |
| `search_players` | "Find all Brazilian players", "Show me all forwards from Santos", "Who are the top Brazilian players?" |
| `get_player` | "Who is Neymar?" |
| `players_by_club` | "Brazilian players at Brazilian clubs" |
| `dataset_info` | What data is loaded, competitions and seasons covered |

Common arguments: `team`, `opponent`, `venue` (home/away/either), `competition`, `season`,
`date_from`/`date_to` (ISO or DD/MM/YYYY), `round` (number, Libertadores stage or `final`), `limit`.

## How the data is handled

- **Team names** differ in every file (`Palmeiras-SP`, `Palmeiras - SP`, `Sao Paulo`,
  `São Paulo`, `EC Bahia`, `Sport Club do Recife`, `C.r.b. - AL`). Names are reduced to an
  accent-folded base name plus a state/country tag; an alias table covers official names
  and renamed clubs (Athletico/Atlético Paranaense). Clubs that share a name stay separate
  (Atlético-MG / Athletico-PR / Atlético-GO, Flamengo-RJ / Flamengo-PI, Botafogo-RJ / -SP / -PB);
  a bare ambiguous name means the best-known club.
- **Duplicates**: a Série A or cup match can appear in up to three files. Later copies are
  merged into the first (keeping scores, corners and shots), so aggregates count each match
  once: 23,953 rows become 16,770 unique matches. `search_matches` with `source` still
  queries any single file in full.
- **Dates**: ISO, ISO with time and DD/MM/YYYY are all accepted. The 2020 league seasons,
  which finished in early 2021, are attributed to 2020.
- **Encoding**: UTF-8 throughout; matching ignores accents and case, output keeps them.
- **Players and matches are linked**: FIFA clubs are mapped to match-data teams, so
  `team_stats` shows the FIFA squad and `get_player` points back to the club's matches.

## Limitations worth knowing

- Standings are calculated from results only (3 points per win); points deductions and
  official tie-breakers are not in the data. The 2023 Série A is missing 3 matches in the
  source data, so its table is labelled incomplete rather than final.
- Relegation is marked as the bottom four of Série A (bottom two in 2003).
- The Copa do Brasil file only numbers rounds up to 2021; for 2021-2023 the final is
  inferred as the last two-legged tie of the season and earlier rounds are unlabelled.
- One Libertadores row (the 2022 final) has no date or score and is skipped.
- The FIFA data has no goal-scorer information, so "top scorers" cannot be answered, and
  it does not include Flamengo, Palmeiras, Corinthians, São Paulo or Vasco squads.
- Penalty shoot-outs are not in the data; a final level on aggregate is reported as such.

## Layout

```
src/soccer.h   shared types and declarations
src/util.c     string buffer, accent folding, dates, CSV reader, JSON parser/writer
src/data.c     CSV loading, team-name normalisation, de-duplication, player-club links
src/query.c    the 14 tools
src/mcp.c      JSON-RPC / MCP dispatcher (initialize, ping, tools/list, tools/call)
src/main.c     stdio server loop and --list / --call helpers
tests/test_bdd.c     Given/When/Then scenarios against the real data (50 scenarios)
tests/test_stdio.sh  end-to-end test of the server binary over stdio
```

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
