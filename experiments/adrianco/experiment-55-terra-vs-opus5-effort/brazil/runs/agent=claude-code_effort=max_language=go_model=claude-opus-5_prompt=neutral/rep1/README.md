# Brazilian Soccer MCP Server

An [MCP](https://modelcontextprotocol.io) server, written in Go with no third-party
dependencies, that turns the six Kaggle CSVs in `data/kaggle/` into a queryable
knowledge graph of Brazilian football and exposes it to an LLM as 20 tools,
5 resources and 5 prompt templates.

Specification: [`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md).

```
16,792 matches (2003-2023)   406 clubs   18,207 players
36,364 graph nodes           111,206 edges          ~160 ms to load
```

## Quick start

```bash
go build -o brazilian-soccer-mcp .   # no network access needed: stdlib only

./brazilian-soccer-mcp               # speak MCP on stdin/stdout
./brazilian-soccer-mcp -list-tools   # the tool catalogue with argument help
./brazilian-soccer-mcp -demo         # answer the built-in sample questions
./brazilian-soccer-mcp -tool standings -args '{"season":2019}'
```

Point an MCP client at the binary, for example in Claude Desktop's
`claude_desktop_config.json` or via `claude mcp add`:

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

The CSVs are found automatically by walking up from the working directory to a
`data/kaggle`; `-data` or `$BRAZIL_SOCCER_DATA` override that. The server makes
no network calls: the optional live APIs in the specification are deliberately
not used, so every answer can be traced back to a row in `data/kaggle/`.

## What it can answer

```
$ ./brazilian-soccer-mcp -tool standings -args '{"season":2019}'
2019 Brasileirão standings (calculated from 380 matches in the provided data):
 1. Flamengo                90 pts (28W,  6D,  4L) GF  86 GA  37 GD  +49 - Champion
 2. Santos                  74 pts (22W,  8D,  8L) GF  60 GA  33 GD  +27
 3. Palmeiras               74 pts (21W, 11D,  6L) GF  61 GA  32 GD  +29
...
Champion: Flamengo. Relegated: Cruzeiro, CSA, Chapecoense, Avaí.

$ ./brazilian-soccer-mcp -tool head_to_head -args '{"team_a":"Flamengo","team_b":"Fluminense","limit":3}'
Flamengo vs Fluminense (Fla-Flu derby):
- 2023-11-11: Flamengo 1-1 Fluminense (Brasileirão 2023)
- 2023-07-16: Fluminense 0-0 Flamengo (Brasileirão 2023)
- 2023-06-02: Flamengo 2-0 Fluminense (Copa do Brasil 2023)
... (41 more meetings in the dataset)

Head-to-head in dataset: Flamengo 18 wins, Fluminense 14 wins, 12 draws (goals 60-48)
```

`internal/soccerserver/questions.go` holds 31 natural-language questions paired
with the tool call that answers each. They are executed by `-demo`, published as
the `soccer://sample-questions` resource, and asserted by `TestSampleQuestions`,
so the list cannot drift away from what the server actually does.

## Tools

| Tool | Answers |
|------|---------|
| `list_datasets` | what is loaded, licences, coverage, known gaps |
| `list_competitions` | competitions, seasons, formats |
| `list_teams` | club catalogue, filtered by name/state/country/competition/season |
| `team_profile` | one club: record, competitions, titles, grounds, derbies, squad |
| `search_matches` | fixtures by club, opponent, venue, competition, season, date, round, stage, result |
| `match_details` | one match with shots, corners, attacks and half-time trend |
| `head_to_head` | every meeting of two clubs plus the derby name |
| `team_stats` | W/D/L, goals, points and win rate under any filter |
| `standings` | league table computed from results, with champion and relegation |
| `season_summary` | league season review, or the cup/Libertadores bracket and winner |
| `compare_seasons` | seasons side by side |
| `league_statistics` | goals per match, home advantage, both-teams-scored, over 2.5 |
| `biggest_wins` | heaviest victories or highest scoring matches |
| `best_records` | clubs ranked by points, win rate, goals for/against, home or away |
| `find_derbies` | matches between traditional rivals |
| `search_players` | FIFA players by name, nationality, club, position, rating, age |
| `player_profile` | one player in full, linked to his club in the match data |
| `club_squads` | squad size, average and best rating per club |
| `graph_neighbors` | typed relationships around any entity |
| `graph_path` | shortest chain of relationships between two entities |

Every tool returns prose for the model to quote and `structuredContent` for the
client to parse.

Resources: `soccer://datasets`, `soccer://teams`, `soccer://competitions`,
`soccer://graph/schema`, `soccer://sample-questions`.
Prompts: `club_dossier`, `season_review`, `derby_briefing`, `answer_question`,
`sample_questions`. Club names, competitions and seasons have argument
completion through `completion/complete`.

## Design

```
main.go                     stdio server, plus -list-tools/-tool/-demo modes
internal/mcp/               MCP over JSON-RPC 2.0: protocol types, schema
                            builder, argument coercion, dispatch loop
internal/soccer/            the domain: loading, name normalisation, the
                            knowledge graph, queries, statistics, formatting
internal/soccerserver/      the 20 tools, resources, prompts, sample questions
```

### The knowledge graph

Nodes are `team`, `player`, `match`, `competition`, `season`, `state`,
`country`, `stadium` and `club`; edges are `home_team`, `away_team`,
`played_in`, `in_season`, `season_of`, `played_at`, `plays_for`, `nationality`,
`based_in`, `in_country` and `rival_of`. Adjacency is kept in both directions,
so `graph_path` can walk from a player to a competition through his club and
its fixtures.

### Team names

The files disagree constantly: `Palmeiras-SP`, `Palmeiras`, `América - MG`,
`América FC (Minas Gerais)`, `Arapongas Esporte Clube - PR`, `A.b.c. - RN`,
`Nacional (URU)`, `Athletico` / `Atletico-PR` / `Atlético Paranaense`. Every
spelling is decomposed into a noise-free base name plus a state or country
qualifier, then resolved through a curated alias table
(`internal/soccer/aliases.go`) and, for everything not curated, an inference
step that joins a bare name to the only state ever seen for it.

Ambiguity is preserved rather than guessed at: `América` returns both
América-MG and América-RN and asks the caller to choose, while
`Flamengo - PI` never becomes Flamengo of Rio.

### Merging the five match files

Série A 2012-2019 appears in three of the files, so rows are keyed by
competition, home club and away club and merged when their dates are within
three days; the richest source wins per field. That is what lets the extended
statistics of `BR-Football-Dataset.csv` and the stadiums of
`novo_campeonato_brasileiro.csv` attach to the same fixture, and what stops
every aggregate from being double counted. 23,852 source rows become 16,792
distinct fixtures.

Three further quirks are handled explicitly and reported through
`list_datasets`:

- **Season boundaries.** `BR-Football-Dataset.csv` only carries a date, and the
  COVID-delayed 2020 Série A ran until 25 February 2021, so league fixtures
  played in January or February belong to the previous season.
- **Misspellings inside a season.** Two 2017 Série B rows spell Vila Nova (GO)
  as "Villa Nova", which is a different club. A stray club that plays far too
  few fixtures for the season and is exactly one edit away from a regular
  participant is reattached; clubs whose names are identical (América-MG and
  América-RN) never are.
- **Rows that cannot belong.** A state championship game filed under "Serie A"
  is dropped when both clubs appear in too few fixtures to be in that league.

### Being honest about the data

Answers are only as strong as the rows behind them:

- A champion is declared only when the season is complete, or when the fixtures
  missing from the sources cannot change the outcome. The 2023 Série A is three
  matches short and Palmeiras, the real champion, still has a game in hand in
  this data, so the server reports the leader and refuses to name a champion.
- Série C and the Libertadores are played in groups and knockouts, so their
  combined tables carry that caveat and never name a champion.
- `fifa_data.csv` is a single FIFA 19 snapshot. Its Brazilian league squads use
  placeholder player names, and Flamengo, Palmeiras, Corinthians, São Paulo and
  Vasco are absent from it entirely - a search for their players says so and
  lists the clubs that are present.
- Nothing in the data records goalscorers, assists, lineups, cards or
  attendances, and the server instructions say so, so the model does not invent
  them.

## Testing

```bash
go test ./...          # includes a build of the binary and a real stdio session
go test -short ./...   # skips the binary build
go vet ./...
```

The suite is behaviour driven: `internal/soccerserver/bdd_test.go` runs the
specification's features as Given/When/Then scenarios (`go test -v` prints the
steps), and the rest covers

- name normalisation and the clubs that must stay apart, dates, numbers, folding;
- the load: row counts per file, fixtures per season, no duplicate fixtures,
  cross-file enrichment, cup stage labelling, the delayed 2020 season;
- computed statistics against seasons whose outcome is a matter of record
  (twelve champions and their points totals, the 2019 table and its relegation);
- the MCP layer: version negotiation, notifications, batches, malformed input,
  argument validation and coercion, tool failures, panics, resources, prompts,
  completion;
- every tool at its edges: ambiguous clubs, unknown competitions, bad argument
  types, empty results;
- the latency budgets from the specification (simple lookups < 2 s, aggregates
  < 5 s);
- the binary itself, driven over its real stdin and stdout.

## Data sources

Kaggle data can't be downloaded without an account so these (freely available
with attribution) data sets have been downloaded for use here:

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
