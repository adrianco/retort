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

## Implementation (Go)

An MCP server, written in Go with no third-party dependencies, that answers
natural-language questions about Brazilian soccer from the six provided
datasets. An LLM host starts it as a subprocess and talks MCP (JSON-RPC 2.0)
over stdin/stdout.

### Build and run

```bash
go build -o brazilian-soccer-mcp .
./brazilian-soccer-mcp -data data/kaggle
```

Example host configuration (e.g. Claude Desktop / Claude Code `mcpServers`):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/path/to/brazilian-soccer-mcp",
      "args": ["-data", "/path/to/data/kaggle"]
    }
  }
}
```

All data is loaded into memory at start-up (about 0.2 s); every query answers
in milliseconds.

### Tools

| Tool | Answers |
|------|---------|
| `search_matches` | Matches by team, opponent, home/away, competition, season, date range or stage (e.g. all Copa do Brasil finals), with head-to-head when two teams are given |
| `last_meeting` | When two teams last met, and the score |
| `head_to_head` | Full head-to-head comparison, per competition |
| `find_derbies` | Matches between traditional rivals (Fla-Flu, Grenal, Derby Paulista...) |
| `team_record` | Win/draw/loss record, goals, points and win rate, by season, competition and venue |
| `rank_teams` | Best home/away records, most goals scored, fewest conceded... |
| `team_competitions` | Which competitions a team has played in |
| `find_team` | Which team a name means, and every spelling the data uses for it |
| `club_profile` | A club's FIFA squad together with its match record (cross-dataset) |
| `standings` | League table calculated from results, champion and relegated teams |
| `knockout_bracket` | Libertadores / Copa do Brasil knockout ties with aggregates and winners |
| `search_players` | Players by name, nationality, club, position (forward/midfielder/...), rating |
| `get_player` | One player's profile and best attributes |
| `brazilian_players_by_club` | Players of a nationality at each Brazilian club, with average rating |
| `competition_stats` | Goals per match, home/draw/away rates, corners and shots where recorded |
| `biggest_wins` | Largest winning margins |
| `compare_seasons` | Season-by-season comparison with champion and top-scoring team |
| `dataset_overview` | What was loaded from each dataset |

Every tool returns readable text for the LLM and the same answer as
`structuredContent`.

### Data handling

- **Team names** are reduced to one key per club: state suffixes
  (`Palmeiras-SP`, `Palmeiras - SP`), accents (`Grêmio`/`Gremio`), full names
  (`Sociedade Esportiva Palmeiras`), club-type words (`FC`, `EC`, `AD`...),
  initials (`C. R. B.`) and known aliases (`Athletico Paranaense`,
  `Atletico-PR`, `Athletico`). Clubs sharing a name but not a state stay apart
  (`Botafogo-RJ` / `Botafogo-PB`, `Santos` / `Santos-AP`).
- **Duplicate matches**: the Série A results, the 2003–2019 archive and the
  extended statistics overlap. A match between the same teams in the same
  competition within three days is recorded once; the extended statistics
  (corners, shots) are attached to it.
- **Dates** in ISO, ISO date-time and Brazilian `DD/MM/YYYY` forms are read.
- **Copa do Brasil stages** are inferred from round numbers (the last round of a
  season, when it is a single tie, is the final).
- Rows without a result (`NA`, `-`: unplayed or abandoned matches) are skipped
  and counted in `dataset_overview`.
- A full-size league season the data does not completely cover (2023: 377 of
  380 matches) gets a provisional table with a leader but no champion.
- In the FIFA data, a club counts as Brazilian when it matches a club in the
  Brazilian domestic match data and is either a major club or has a mostly
  Brazilian squad (so Portugal's Boavista FC isn't mistaken for Boavista-RJ).
  The FIFA data has no Flamengo, Palmeiras, São Paulo or Corinthians squads,
  and the server says so rather than guessing.

### Tests: Acceptance Test-Driven Development

The system was specified with executable acceptance tests before it was built,
following Dave Farley's four-layer model:

1. **Specifications** (`acceptance/*_test.go`) in the language of the problem
   domain, for example:
   ```go
   s.Matches.Played("home: Flamengo", "away: Fluminense", "score: 2-1", "date: 2023-09-03")
   s.Matches.Search("team: Flamengo", "opponent: Fluminense")
   s.Matches.ConfirmFound("Flamengo 2-1 Fluminense on 2023-09-03")
   ```
2. **DSL** (`acceptance/dsl`): `name: value` parameters with defaults, split by
   domain area (matches, teams, players, competitions, statistics).
3. **Protocol driver** (`acceptance/driver`): the only test code that knows the
   server is an MCP process reading CSV files. For each spec it writes a
   synthetic dataset in the provided files' formats, starts the real server
   binary and calls its tools over stdio.
4. **System under test**: the server itself (`main.go`, `internal/`).

Most specs run against small synthetic datasets that state exactly the facts
they need. `acceptance/provided_data_test.go` runs against the real Kaggle data:
data coverage, response times (< 2 s simple, < 5 s aggregate), well-known
historical facts (2019 champion Flamengo on 90 points, 2020 relegations, the
2018 Libertadores final) and 23 of the sample questions from the specification.

```bash
go test ./...                 # unit tests + acceptance specs
go test ./acceptance/ -v      # the executable specification, spec by spec
```

The acceptance suite builds the server binary once in `TestMain`. To run the
specs against a binary built elsewhere, set `SOCCER_SERVER_BINARY`; to use
another copy of the data, set `SOCCER_DATA_DIR`.
