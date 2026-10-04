# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server, written in Go with only the standard
library, that answers questions about Brazilian football from the provided
Kaggle datasets: Brasileirão (2003-2023), Série B/C, Copa do Brasil and Copa
Libertadores matches, and FIFA 19 player ratings. Connect it to an LLM client
and ask things like "Who won the 2019 Brasileirão?" or "Compare Palmeiras and
Santos head-to-head".

The specification is in `TASK.md` (and `brazilian-soccer-mcp-guide.md`).

## Running

```sh
go build -o brsoccer .
./brsoccer -data data/kaggle        # speaks MCP (JSON-RPC 2.0) on stdin/stdout
```

The data directory can also be set with `SOCCER_DATA_DIR`. Loading all six
files and merging them takes about 0.2 s; queries take milliseconds.

Example client configuration (Claude Desktop / Claude Code `.mcp.json`):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/brsoccer",
      "args": ["-data", "/absolute/path/to/data/kaggle"]
    }
  }
}
```

## Tools

Every tool returns a readable text answer (formatted like the examples in
`TASK.md`) plus `structuredContent` JSON with the same facts.

| Tool | Answers questions like |
|------|------------------------|
| `find_matches` | "Show me all Flamengo vs Fluminense matches" (with head-to-head summary), "What matches did Palmeiras play in 2023?", "Find all Copa do Brasil finals" (`stage: final`), "When did Flamengo last play Corinthians?" (`limit: 1`), date ranges, home/away only |
| `team_record` | "What is Corinthians' home record in 2022?" |
| `head_to_head` | "Compare Palmeiras and Santos head-to-head" |
| `rank_teams` | "Which team scored the most goals in Serie A 2023?", "Which team has the best away record?" |
| `team_competitions` | "What competitions has Palmeiras played in?" |
| `team_overview` | A club's results across competitions combined with its FIFA squad (cross-file) |
| `standings` | "Who won the 2019 Brasileirão?", "Which teams were relegated in 2020?" |
| `knockout_bracket` | "Show the 2018 Copa Libertadores bracket" |
| `competition_stats` | "What's the average goals per match in the Brasileirão?", home win rate |
| `compare_seasons` | "Compare the 2018 and 2019 seasons" |
| `biggest_wins` | "Show me the biggest wins in the dataset" |
| `derbies` | "Show me all derbies in 2023" (Fla-Flu, Grenal, Derby Paulista, ...) |
| `search_players` | "Who is Gabriel Barbosa?" (suggests similar names when absent), "Find all Brazilian players", "Show me all forwards from Grêmio" |
| `players_by_club` | "Brazilian players at Brazilian clubs" (links FIFA clubs to clubs in the match data) |
| `list_datasets` | Which files are loaded and how many records each holds |

## How the data is reconciled

* **Team names** are normalised across every naming style in the data
  ("Palmeiras-SP", "Palmeiras - SP", "Botafogo RJ", "Nacional (URU)",
  "Sport Club Corinthians Paulista", "América FC (Minas Gerais)"), accents are
  optional, and clubs sharing a name are kept apart by state (Atlético-MG,
  Athletico-PR and Atlético-GO; Flamengo-RJ and Flamengo-PI). A name without
  a state takes the state it most often appears with.
* **Dates** in ISO, ISO-with-time and Brazilian `DD/MM/YYYY` formats are understood.
* **The same match in several files is counted once.** Records of the same
  competition, home and away clubs within three days are merged (the
  preferred file's facts win, gaps such as missing scores, stadiums and
  corner/shot statistics are filled from the others). Because the Série A is
  a double round-robin, a home/away pairing in one Série A season is also
  treated as one match across files. Every Série A season 2006-2022 comes out
  at exactly 380 matches and 20 clubs.
* Fixtures with no score in any file are left out of all statistics.
* Copa do Brasil stages are derived from round numbers (the last round is
  the final when it is a single two-legged tie).

See `docs/atdd-findings.md` for the data-quality problems the acceptance
tests surfaced.

## Tests: acceptance-test-driven development

The system was built with Dave Farley's Acceptance Test-Driven Development
four-layer model. Executable specifications were written first, in the
language of the problem domain, then the DSL, then the protocol driver, then
the system.

```
acceptance/*_test.go      1. Test cases - executable specifications, Given/When/Then, domain language only
acceptance/dsl/           2. DSL - Records, Matches, Teams, Players, Competitions, Statistics, Datasets;
                             "key: value" params with defaults, generated dates/ids
acceptance/drivers/       3. Protocol drivers - MCPDriver (launches the binary, speaks MCP over stdio,
                             makes every assertion); RecordsStub (writes records in the real CSV formats)
main.go, internal/        4. The system under test
```

For example:

```go
func TestCompetitions_ShouldCalculateTheChampionFromResults(t *testing.T) {
	s := dsl.NewScenario(t)
	s.Records.Match("season: 2019", "home: Flamengo-RJ", "away: Santos-SP", "score: 3-0")
	s.Records.Match("season: 2019", "home: Santos-SP", "away: Palmeiras-SP", "score: 1-1")
	s.Records.Match("season: 2019", "home: Palmeiras-SP", "away: Flamengo-RJ", "score: 0-2")

	s.Competitions.Standings("season: 2019")

	s.Competitions.ConfirmChampion("Flamengo", "points: 6", "wins: 2")
}
```

* Most specs create their own synthetic records, and each one gets a
  private instance of the server, so they are isolated and run in parallel.
* `acceptance/provided_data_test.go` checks the provided datasets themselves:
  all six files load, more than 20 sample questions from `TASK.md` are
  answered correctly (checked against values computed independently), and
  responses come back within the 2 s / 5 s limits.
* Unit tests in `internal/` cover name normalisation, dates, merging and the
  MCP protocol.

```sh
go test ./...                                   # everything
go test ./acceptance/ -run ProvidedData -v      # just the provided-data specs
SOCCER_SYSTEM_BINARY=/path/to/brsoccer go test ./acceptance/   # test a pre-built release candidate
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
