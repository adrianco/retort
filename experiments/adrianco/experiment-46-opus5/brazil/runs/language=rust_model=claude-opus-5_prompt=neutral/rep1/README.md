# Brazilian Soccer MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) server, written in Rust with no
runtime services to install, that answers natural-language questions about Brazilian soccer from
the six Kaggle CSV files in `data/kaggle/`. The specification it implements is
[TASK.md](TASK.md) / [brazilian-soccer-mcp-guide.md](brazilian-soccer-mcp-guide.md).

The server builds an in-memory knowledge graph at startup (~110 ms) and answers every documented
query in well under a millisecond.

```
Graph: 395 teams, 23,953 matches (16,824 canonical after de-duplication), 18,207 players,
       72,159 edges — built from 42,140 CSV rows in ~110 ms.
```

## Quick start

```bash
cargo build --release

# 1. Speak MCP over stdio (this is what an LLM host launches)
cargo run --release

# 2. Answer the specification's sample questions and print the results
cargo run --release -- demo

# 3. One-shot tool call from the shell
cargo run --release -- ask standings '{"competition":"Serie A","season":2019}'
cargo run --release -- ask head_to_head '{"team_a":"Flamengo","team_b":"Fluminense"}'

# 4. List the tools
cargo run --release -- tools

cargo test          # 94 tests: unit + BDD integration + MCP protocol conformance
```

Register it with an MCP host (Claude Desktop / Claude Code `mcpServers` config):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/target/release/brazilian-soccer-mcp",
      "env": { "BRAZILIAN_SOCCER_DATA_DIR": "/absolute/path/to/data/kaggle" }
    }
  }
}
```

## What it answers

| Capability | Tools | Example question |
|---|---|---|
| Match queries | `search_matches`, `head_to_head` | *"Show me all Flamengo vs Fluminense matches"* |
| Team queries | `team_stats`, `team_profile`, `find_team` | *"What is Corinthians' home record in 2022?"* |
| Player queries | `search_players`, `player_profile`, `club_players` | *"Who are the highest-rated players at Grêmio?"* |
| Competition queries | `standings`, `competition_stats` | *"Who won the 2019 Brasileirão?"* |
| Statistical analysis | `team_rankings`, `biggest_wins`, `competition_stats` | *"Which team has the best away record?"* |
| Graph / provenance | `graph_neighbors`, `dataset_overview` | *"What data is loaded and what are its limits?"* |

Sample answers (from `cargo run --release -- demo`, which runs all 33 questions in
[`src/samples.rs`](src/samples.rs)):

```
Q: Who won the 2019 Brasileirão?
   2019 Brasileirão Série A table (calculated from 380 matches in the dataset):
    1. Flamengo - 90 pts (28W, 6D, 4L) GF 86 GA 37 GD +49 - Champion
    2. Santos - 74 pts (22W, 8D, 8L) GF 60 GA 33 GD +27
    3. Palmeiras - 74 pts (21W, 11D, 6L) GF 61 GA 32 GD +29

Q: Show me all Flamengo vs Fluminense matches
   - 2023-11-11: Flamengo 1-1 Fluminense (Brasileirão Série A)
   - 2023-06-02: Flamengo 2-0 Fluminense (Copa do Brasil)
   ... (34 more matches in the dataset)
   Head-to-head in dataset: Flamengo 18 wins, Fluminense 14 wins, 12 draws (goals 60-48)
```

Every tool returns both a natural-language answer (`content[0].text`) and a machine-readable
`structuredContent` payload.

## Tools

| Tool | Purpose |
|---|---|
| `search_matches` | Matches by team, opponent, home/away side, competition, season, date range or stage |
| `head_to_head` | Two clubs compared: record, per-competition split, recent meetings |
| `team_stats` | W/D/L, goals, points, win rate — filterable by season, competition, home/away |
| `team_profile` | Competitions and seasons a club appears in, name variants, linked FIFA squad |
| `standings` | League table calculated from results, with champion and relegation when a season is complete |
| `competition_stats` | Goals per match, home/draw/away split, per-season breakdown, season comparison |
| `team_rankings` | Clubs ranked by points, wins, win rate, goals for/against, goal difference, clean sheets |
| `biggest_wins` | Largest margins, optionally scoped to a competition, season or club |
| `search_players` | FIFA database by name, nationality, club, position, rating, age |
| `player_profile` | One player: ratings, attributes, club, link into the match data |
| `club_players` | A club's FIFA squad plus its match-data footprint |
| `find_team` | Resolve/disambiguate a club name and show every spelling in the data |
| `graph_neighbors` | Traverse the knowledge graph from a team, match, player or competition node |
| `dataset_overview` | Files, licenses, row counts, coverage, graph size, caveats |

The server also exposes MCP **resources** (`soccer://overview`, `soccer://teams`,
`soccer://competitions`, `soccer://source/<file>`) and two **prompts** (`club_report`,
`season_review`).

## Design

```
src/data.rs       CSV ingestion — header-indexed, tolerant of dirty rows
src/normalize.rs  club-name folding: accents, state suffixes, filler words, aliases
src/model.rs      entities: Date, Competition, Source, Team, Match, Player, Record
src/graph.rs      KnowledgeGraph — identity resolution, de-duplication, adjacency
src/queries.rs    analytics: searches, head-to-head, tables, rankings, averages
src/format.rs     natural-language answers + structured JSON
src/tools.rs      MCP tool schemas, argument validation, dispatch
src/mcp.rs        JSON-RPC 2.0 over newline-delimited stdio
src/samples.rs    the worked questions used by both the demo and the tests
```

Nodes are teams, matches, players and competitions; edges are `hosted` / `visited` /
`home_team` / `away_team` / `part_of` / `includes` / `plays_for` / `has_player`. Adjacency is
materialised at build time, so every query is a slice scan rather than a table join.

### The two hard problems in this data

**1. One club, many spellings.** The files disagree constantly — `Palmeiras-SP`, `SE Palmeiras`,
`Palmeiras`; `Atlético-PR` vs `Athletico Paranaense`; `EC Bahia` vs `Bahia`; `Nacional (URU)` vs
`Nacional-URU`; `Sport Club do Recife` vs `Sport-PE`; `A.b.c. - RN` vs `ABC - RN`. Names are
folded to a canonical key of *base name + state (UF) or country code* by stripping accents,
punctuation, trailing state/country qualifiers, club-type filler (`EC`, `FC`, `Clube`,
`Esporte`, …) and stray initials, then applying an alias table for the spellings no rule can
derive. A final pass folds an unqualified spelling (`Santos`) into a qualified one (`Santos-SP`)
when that is unambiguous — while keeping genuinely different clubs apart (`América-MG` vs
`América-RN`, three separate `Atlético`s). Ambiguous queries are reported as such rather than
guessed:

```
$ cargo run -- ask team_stats '{"team":"Atlético"}'
'Atlético' is ambiguous. Did you mean: Atlético-MG, Atlético-GO, Atlético-AC, …?
```

**2. Six files that overlap.** Série A 2019 appears in three files; the Copa do Brasil in two.
Counting them all would inflate every aggregate threefold. For each (competition, season) one
file is chosen as **canonical** — by a per-competition preference order, unless the preferred
file is materially less complete (the Brasileirão file was scraped mid-2022 and has 81 fixtures
with `NA` scores, so 2022 falls back to the BR-Football file). Non-canonical rows stay queryable
via `include_all_sources: true`, and `standings`/`dataset_overview` report which file an answer
came from.

### Honesty about gaps

The server never fills a hole with a guess:

* **No goalscorer data** exists in any file, so "top scorer" questions are declined and redirected
  to team scoring records.
* **FIFA 19 is a 2019 snapshot with only licensed Brazilian clubs** — Flamengo, Palmeiras,
  Corinthians, São Paulo and Vasco have no squads. `club_players` says so and lists the 15 clubs
  that do have player data; asking for `Gabriel Barbosa` explains that the snapshot predates his
  Flamengo spell and suggests similar names.
* **A same-named foreign club is not silently merged**: FIFA's `Boavista FC` (Portugal) is kept
  apart from Boavista-RJ, because a Brazilian club's FIFA squad is overwhelmingly Brazilian and
  that one is not.
* **Fixtures without a result** are printed as "no result recorded", never as 0-0, and are
  excluded from records.
* **Partial seasons** are flagged, and no champion or relegation is inferred from an incomplete
  table or from a knockout competition.

## Tests

`cargo test` runs 94 tests, all against the real datasets:

| File | Covers |
|---|---|
| `src/*.rs` unit tests | date parsing, name normalization, competition parsing, record maths |
| `tests/bdd_match_queries.rs` | match search, filters, sorting, error handling |
| `tests/bdd_team_queries.rs` | team statistics, head-to-head symmetry, rankings |
| `tests/bdd_player_queries.rs` | player search, profiles, squads, cross-file club links |
| `tests/bdd_competition_queries.rs` | standings, champion/relegation, table consistency |
| `tests/bdd_statistics.rs` | averages, biggest wins, de-duplication, home advantage |
| `tests/bdd_data_quality.rs` | name variants, date formats, UTF-8, canonical-source selection |
| `tests/mcp_protocol.rs` | handshake, tools/list, tools/call, resources, prompts, JSON-RPC errors, full stdio session |
| `tests/sample_questions.rs` | all 33 sample questions answered inside the 2 s / 5 s latency budget |

Tests are written in Given/When/Then form, e.g.:

```rust
#[test]
fn scenario_find_matches_between_two_teams() {
    // GIVEN the match data is loaded
    given_the_knowledge_graph_is_loaded();
    // WHEN I search for matches between "Flamengo" and "Fluminense"
    let answer = when_i_call("search_matches", json!({"team": "Flamengo", "opponent": "Fluminense"}));
    // THEN I should receive a list of matches with date, scores and competition
    ...
}
```

Facts asserted against reality, not just against the code: Flamengo's 90-point 2019 title, the
2020 relegation of Vasco/Goiás/Coritiba/Botafogo, Corinthians' 19 home matches in 2022, the
2019 Libertadores final.

## Data sources

Kaggle data can't be downloaded without an account, so these (freely available with attribution)
data sets have been downloaded for use here:

https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro
- License: Attribution 4.0 International (CC BY 4.0)
- data/kaggle/Brasileirao_Matches.csv — Série A 2012-2022, 4,180 matches
- data/kaggle/Brazilian_Cup_Matches.csv — Copa do Brasil 2012-2021, 1,337 matches
- data/kaggle/Libertadores_Matches.csv — Libertadores 2013-2022, 1,254 matches

https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches
- License: CC0: Public Domain
- data/kaggle/BR-Football-Dataset.csv — Série A/B/C and Copa do Brasil 2014-2023 with shots,
  corners and attacks, 10,296 matches

https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019
- License: World Bank - Attribution 4.0 International (CC BY 4.0)
- data/kaggle/novo_campeonato_brasileiro.csv — Série A 2003-2019 with stadiums, 6,886 matches

https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data
- License: Apache 2.0
- data/kaggle/fifa_data.csv — 18,207 FIFA 19 players, 827 of them Brazilian

Demo / non-commercial use, per the specification.
