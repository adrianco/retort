# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server, written in Go with no external
dependencies, that exposes a knowledge graph over the Brazilian football
datasets in `data/kaggle` as tools an LLM can call.

## Specification

`TASK.md` / `brazilian-soccer-mcp-guide.md`

## Quick start

```bash
go build -o brazilian-soccer-mcp .

# serve MCP over stdio (this is what an MCP client launches)
./brazilian-soccer-mcp

# explore from the command line
./brazilian-soccer-mcp -list
./brazilian-soccer-mcp -call standings      -args '{"season":2019,"top":5}'
./brazilian-soccer-mcp -call head_to_head   -args '{"team_a":"Flamengo","team_b":"Fluminense","limit":5}'
./brazilian-soccer-mcp -call search_players -args '{"nationality":"Brazil","limit":10}'
```

Register it with an MCP client (e.g. Claude Code) as a stdio server:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/brazilian-soccer-mcp",
      "args": ["-data", "/absolute/path/to/data/kaggle"]
    }
  }
}
```

Diagnostics go to stderr; stdout carries only the JSON-RPC stream.

## Layout

| Path | Contents |
|------|----------|
| `main.go` | entry point: loads the data, registers the tools, serves stdio (or runs one tool with `-call`) |
| `mcp/` | the MCP protocol: JSON-RPC framing, `initialize`, `tools/list`, `tools/call`, tolerant argument decoding |
| `soccer/` | the knowledge graph: CSV loading, name normalisation, queries, statistics, text rendering |
| `tools/` | tool schemas and handlers wiring `soccer` onto `mcp` |
| `data/kaggle/` | the six source CSV files |

Every file starts with a context comment explaining what it is responsible for.

## Tools

| Tool | Answers questions like |
|------|------------------------|
| `search_matches` | "Show me all Flamengo vs Fluminense matches", "What matches did Palmeiras play in 2023?", "Find all Copa do Brasil finals" |
| `head_to_head` | "Compare Palmeiras and Santos head-to-head" |
| `team_stats` | "What is Corinthians' home record in 2022?" |
| `standings` | "Who won the 2019 Brasileirão?", "Which teams were relegated in 2020?" |
| `rank_teams` | "Which team has the best away record?", "Which team scored the most goals in Série A 2019?" |
| `competition_stats` | "What's the average goals per match in the Brasileirão?", "Compare the 2018 and 2019 seasons" |
| `biggest_wins` | "Show me the biggest wins in the dataset" |
| `search_players` | "Find all Brazilian players", "Show me all forwards from Santos" |
| `get_player` | "Who is Gabriel Jesus?" |
| `club_squads` | "Which Brazilian clubs have the strongest squads?" (joins FIFA data to the match data) |
| `list_teams` / `list_competitions` / `dataset_info` | coverage and name resolution |

Every tool returns both a human-readable text block (what the model reads) and
`structuredContent` (typed JSON for programmatic clients).

## How the data is handled

**One graph from six files.** 23,954 raw rows collapse to ~17,800 unique
matches plus 18,207 players. The same fixture appears in up to three files; it
is merged on (competition, clubs, date ±1 day — sources disagree about late
kick-offs by a day) so aggregates are not double counted. Merged records keep
every source name, and the extended per-match statistics (corners, shots,
attacks) from `BR-Football-Dataset.csv` are carried onto the merged fixture.

**Team name normalisation.** `soccer/normalize.go` folds accents, drops
parentheticals and generic club words, and strips state/country suffixes, so
`Palmeiras-SP`, `Palmeiras` and `Sociedade Esportiva Palmeiras` are one node.
Clubs that are only unique with their state keep it (`Atlético-MG` ≠
`Athletico-PR` ≠ `Atlético-GO`), and an alias table covers the spellings the
rules cannot derive (`Athletico`/`Atlético Paranaense`, `Sport`/`Sport Recife`,
`Vasco`/`Vasco da Gama RJ`).

**Dates and encoding.** ISO, ISO-with-time and Brazilian `DD/MM/YYYY` dates are
all parsed; goal counts arrive quoted, bare or as floats. UTF-8 is preserved in
output (`São Paulo`, `Grêmio`, `Maracanã`) while queries are accent-insensitive.

Correctness check: the computed 2019 Série A table reproduces the real one —
Flamengo champion on 90 points from 38 matches, 20 clubs — and every season from
2006 on has exactly 20 clubs playing 38 matches.

## Testing

```bash
go test ./...          # unit + BDD scenarios + end-to-end tool calls
go test -race ./...
```

BDD Given/When/Then scenarios live in `soccer/soccer_test.go` as subtests named
after the Gherkin scenarios in the specification, covering match, team, player,
competition and statistical queries. `soccer/normalize_test.go` and
`soccer/load_test.go` cover name/date normalisation and cross-file
deduplication. `mcp/server_test.go` drives the protocol itself. `tools/tools_test.go`
asks 26 of the specification's sample questions through real `tools/call`
JSON-RPC requests and asserts on the answers, including the performance budgets
(<2s simple lookups, <5s aggregates — actual timings are milliseconds; the whole
dataset loads in ~130 ms).

## Known data limitations

These are properties of the source data, not the server:

- `fifa_data.csv` is the FIFA 19 snapshot and only includes licensed Brazilian
  clubs — Grêmio, Santos, Internacional, Cruzeiro and so on are present, but
  Flamengo, Palmeiras, Corinthians and São Paulo are not, so player queries for
  those clubs return nothing.
- There are no goalscorer or lineup columns anywhere in the data, so
  "top scorers" cannot be answered; only team level scoring is available.
- A handful of `BR-Football-Dataset.csv` rows carry a competition label that
  disagrees with the other sources (e.g. one 2016 fixture tagged Série A that
  adds two stray clubs to that table).
- Copa do Brasil stage names are inferred from the round number.

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
