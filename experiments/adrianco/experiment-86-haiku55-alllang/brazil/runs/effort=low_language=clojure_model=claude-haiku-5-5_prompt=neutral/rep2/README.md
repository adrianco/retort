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

## Implementation (Clojure MCP server)

An MCP server over stdio (JSON-RPC 2.0, newline-delimited) that answers questions about the datasets above. It has no external dependencies; it runs on the Clojure CLI alone.

### Run

```sh
clojure -M:server                 # reads data/kaggle (or $BRAZIL_SOCCER_DATA, or a path argument)
clojure -M:test                   # runs the test suite (43 tests)
```

Example MCP client configuration:

```json
{ "mcpServers": { "brazilian-soccer": {
    "command": "clojure",
    "args": ["-M:server", "/absolute/path/to/data/kaggle"] } } }
```

### Tools

| Tool | Answers |
|------|---------|
| `search_matches` | Matches by team, opponent, competition, season, date range, venue |
| `team_record` | Wins/draws/losses, goals and win rate for a team |
| `head_to_head` | All meetings between two teams |
| `standings` | League table calculated from results (3/1/0 points) |
| `league_stats` | Goals per match, home/away/draw rates, biggest wins |
| `search_players` | FIFA players by name, nationality, club, position, minimum overall |
| `brazilian_club_summary` | Brazilian players per club with average overall |

### Layout

- `src/brazilian_soccer/csv.clj`, `json.clj`: CSV reader and JSON codec (no libraries)
- `src/brazilian_soccer/names.clj`: team and competition name normalization
- `src/brazilian_soccer/data.clj`: loads the six CSVs into match and player records
- `src/brazilian_soccer/queries.clj`: pure query functions
- `src/brazilian_soccer/tools.clj`: tool definitions and text formatting
- `src/brazilian_soccer/server.clj`: JSON-RPC stdio loop
- `test/brazilian_soccer/`: unit tests, fixture-based exact-value tests, and smoke tests on the real data

### Data handling decisions

- **Team names.** State suffixes (`Palmeiras-SP`), parentheticals (`Nacional (URU)`), accents and case are normalized. Known spelling variants are mapped explicitly (`Sport Club Corinthians Paulista`, `Vasco`, `Athletico-PR`, `Atletico Paranaense`, ...). The three Atlético clubs are kept apart by state code, since they share a base name.
- **Duplicates.** The same match appears in several files. Files are merged in priority order (Brasileirão, Cup, Libertadores, historical, BR-Football). A match counts as a duplicate when the same teams produced the same score within one day, because BR-Football stores some dates one day off.
- **BR-Football scope.** Its Brasileirão and Copa rows are used only for competition-seasons that no primary file covers. Where they overlap, the primary file wins.
- **Dates.** ISO (`2023-09-24`, `2012-05-19 18:30:00`) and Brazilian (`29/03/2003`) formats are both accepted.

### Known limitations

- Source data gaps: the Brasileirão file has 268 rows for 2020 and 299 for 2022 (a full season is 380), and 492 rows for 2021 (more than a 20-team season produces). Standings for those seasons are incomplete or inflated. 2023 comes only from BR-Football and has 377 matches.
- The 2019 standings match the spec's example table (Flamengo 90 pts, 28W 6D 4L; Santos and Palmeiras 74). The other seasons from 2012 to 2019 have the expected 380 matches and 38 games per team, but I have not checked their tables against published results.
- Startup loads all datasets in about 9 seconds. Each query then takes 4–11 ms.
- Cup finals can't be filtered by round directly. Search by competition and season; the round is shown in each result.
- Team-name matching is by name, so a team that changed its name between sources may still need an alias in `names.clj`.
- Only the spec's core questions are covered. The optional API-Football and TheSportsDB sources are not used.
