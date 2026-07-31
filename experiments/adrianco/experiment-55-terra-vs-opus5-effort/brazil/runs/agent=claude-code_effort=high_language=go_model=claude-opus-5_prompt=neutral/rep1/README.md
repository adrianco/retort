# Brazilian Soccer MCP Server

An [MCP](https://modelcontextprotocol.io) server, written in Go, that turns the
six Kaggle CSV files in `data/kaggle/` into a queryable knowledge graph of
Brazilian soccer and exposes it to an LLM as 14 tools, 3 resources and 2
prompts.

It answers questions such as *"Who won the 2019 Brasileirão?"*, *"What is
Corinthians' home record in 2022?"*, *"Show me all Flamengo vs Fluminense
matches"* and *"Who are the top Brazilian players?"* — computing every answer
from the raw match results rather than looking it up in a standings file.

```
$ brazilian-soccer-mcp -ask standings -args '{"competition":"serie-a","season":2019}'

2019 Campeonato Brasileiro Série A — table calculated from match results

#   Team                       P   W   D   L   GF   GA   GD  Pts
1   Flamengo                  38  28   6   4   86   37  +49   90  Champion
2   Santos                    38  22   8   8   60   33  +27   74
3   Palmeiras                 38  21  11   6   61   32  +29   74
...
17  Cruzeiro                  38   7  15  16   27   46  -19   36  Relegated
18  CSA                       38   8   8  22   24   58  -34   32  Relegated
19  Chapecoense               38   7  11  20   31   52  -21   32  Relegated
20  Avaí                      38   3  11  24   18   62  -44   20  Relegated

Champion: Flamengo
Relegated: Cruzeiro, CSA, Chapecoense, Avaí
Matches used: 380 of 380 expected.
```

For all twenty complete Série A seasons in the data (2003–2022) the
reconstructed table names the correct champion and the correct four relegated
clubs. Those numbers are derived, not transcribed, and a test pins them.

---

## Quick start

```bash
go build -o brazilian-soccer-mcp .   # the CSVs are embedded in the binary
go test ./...                        # full test suite, ~5s

./brazilian-soccer-mcp               # speak MCP over stdio (what a client does)
./brazilian-soccer-mcp -demo         # answer the 28 sample questions and exit
./brazilian-soccer-mcp -ask search_matches -args '{"team":"Flamengo","opponent":"Fluminense","limit":5}'
```

| Flag | Purpose |
|------|---------|
| *(none)* | Serve MCP over stdio |
| `-demo` | Run every catalogued sample question through a real MCP round trip |
| `-ask <tool> -args <json>` | Call one tool from the shell |
| `-data <dir>` | Read the CSVs from disk instead of the embedded copies |
| `-version` | Print the version |

### Connecting an MCP client

Claude Desktop / Claude Code (`claude_desktop_config.json` or `.mcp.json`):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/brazilian-soccer-mcp"
    }
  }
}
```

The datasets are embedded in the binary, so it can be launched from any working
directory. Logging goes to stderr; stdout carries only protocol traffic.

---

## Tools

| Tool | Answers questions like |
|------|------------------------|
| `dataset_info` | *What data is this server working from?* |
| `list_competitions` | *What competitions and seasons are available?* |
| `search_teams` | *Which clubs are called Atlético?* |
| `search_matches` | *Show me all Flamengo vs Fluminense matches.* *Find all Copa do Brasil finals.* *Show me the biggest wins.* |
| `head_to_head` | *Compare Palmeiras and Santos head-to-head.* |
| `team_stats` | *What is Corinthians' home record in 2022?* *What competitions has Palmeiras played in?* |
| `standings` | *Who won the 2019 Brasileirão?* *Which teams were relegated in 2020?* |
| `competition_bracket` | *Show the 2018 Copa Libertadores bracket.* |
| `league_stats` | *What's the average goals per match?* *Which team has the best away record?* |
| `compare_seasons` | *Compare the 2018 and 2019 seasons.* |
| `search_players` | *Who are the top Brazilian players?* *Show me all forwards at Atlético Mineiro.* |
| `player_profile` | *Who is Neymar Jr?* |
| `club_squad` | *Which players play for Grêmio?* (joins the player and match datasets) |
| `derbies` | *Show me all derbies in 2023.* |

Every tool returns **both** a formatted text block — laid out the way the
specification's "Example answer format" sections show, so the model can quote it
directly — and the same answer as schema-validated structured JSON.

**Resources:** `soccer://datasets`, `soccer://teams`, `soccer://competitions`.
**Prompts:** `club_report`, `season_review`.

---

## What is in the graph

| Node | Count | Notes |
|------|-------|-------|
| Teams | 382 | canonical clubs, reconciled from ~700 raw spellings |
| Matches | 16,762 | after merging 7,090 duplicate rows across overlapping datasets |
| Players | 18,207 | FIFA 19 snapshot; 827 of them Brazilian |
| Competitions | 5 | Série A/B/C, Copa do Brasil, Copa Libertadores |

| Competition | Seasons | Matches | Clubs |
|-------------|---------|---------|-------|
| Campeonato Brasileiro Série A | 2003–2023 | 8,404 | 47 |
| Campeonato Brasileiro Série B | 2014–2023 | 3,677 | 60 |
| Campeonato Brasileiro Série C | 2014–2023 | 1,801 | 73 |
| Copa do Brasil | 2012–2023 | 1,627 | 281 |
| Copa Libertadores | 2013–2022 | 1,253 | 107 |

Loading all six files and building every index takes about 0.65 s. Queries then
run against in-memory indexes: simple lookups are sub-millisecond and a
corpus-wide aggregate over all 16,762 matches takes a few milliseconds — well
inside the specification's 2 s / 5 s budgets, which the test suite enforces.

---

## The interesting part: making five inconsistent datasets agree

Most of the work in this server is data reconciliation. Each decision below is
implemented in one place, commented where it lives, and pinned by a test.

**Club names** (`normalize.go`, `aliases.go`). The same club appears as
`Palmeiras-SP`, `Palmeiras`, `Atlético - MG`, `Atletico Mineiro`,
`Sport Club do Recife` and `A.b.c. - RN`. Each raw name is decomposed into a
`(base, region)` pair: diacritics are folded, a trailing state or country code
is peeled off in any of its five punctuation styles, parentheticals and
club-type noise (`FC`, `EC`, `Futebol Clube`, single-letter initials) are
dropped, and the remainder is slugged. The region is part of the identity, so
Atlético-MG, Athletico-PR and Atlético-GO stay three distinct clubs — while
`Athletico`, `Atletico Paranaense` and `Atlético-PR` all reach the same node.

**Duplicate fixtures** (`load.go`). Série A 2014–2019 appears in three of the
five match files. Rows are merged on `(competition, season, home, away)` when
their dates are close together, in dataset-priority order, with every source
recorded on the surviving match — so a fixture keeps the round number from one
file, the stadium from another and the shot counts from a third. 7,090 rows are
folded away; without this every league table would be double-counted.

**A mislabelled state column.** `novo_campeonato_brasileiro.csv` records
Vitória — a Bahia club — with `Mandante_UF = ES` in 179 rows. Trusting the
column splits the club in two and corrupts every table it appears in, so the
curated default region deliberately outranks the state column when resolving.

**A season that ran into the next year.** COVID pushed the 2020 Série A into
February 2021. `BR-Football-Dataset.csv` has no season column, so a naive
year-of-date mapping moves 111 matches into 2021 and breaks both seasons.
Brazilian leagues never play in January or February, so league matches in those
months are attributed to the previous season.

**Knockout stages.** The Copa do Brasil file carries bare round numbers. Stages
are inferred from *how many matches a round contains* (2 → final, 4 →
semifinals, 8 → quarterfinals, 16 → round of 16) rather than from the round's
position, because the 2021 season stops after the round of 16 — counting back
from the last round present would label a round-of-16 tie as a final. Rounds
before the largest round are skipped, since 2013–2015 open with a single
two-legged preliminary tie that would otherwise look like a final. The result is
the nine correct Copa do Brasil finals for 2012–2020.

**Rows that are not what they claim.** A Campeonato Brasiliense fixture
(Brasília FC vs CA Taguatinga, 2016-01-30) is labelled "Serie A". Clubs that
played fewer than a quarter of the busiest club's matches are excluded from a
league table and named in a note, rather than silently distorting it.

**Linking players to clubs.** FIFA club names are matched against the match-data
club graph, but name matching alone is not enough: FIFA also contains Boavista
FC and CD Nacional of Portugal and Club América of Mexico, whose names collide
with Boavista-RJ, Nacional-AM and América-MG. A club is only linked when its
squad is at least 60% Brazilian, which yields exactly the 15 Brazilian clubs
FIFA 19 licenses.

**Saying "I don't know".** A champion is only named when every fixture of a
season is present (2023 is three matches short, so no champion is asserted). An
ambiguous club name returns the candidate list instead of a guess. A club FIFA
does not license returns an empty squad plus the list of clubs it does cover. A
missing player returns the nearest names. No file here records goalscorers, and
the server's instructions say so rather than letting the model invent one.

---

## Layout

```
main.go, embed.go              command line; the CSVs embedded in the binary
internal/soccer/               the knowledge graph and query engine
  normalize.go, aliases.go       team-name normalisation and curated aliases
  dates.go                       the three date formats present in the data
  model.go                       Team / Match / Player / Competition nodes
  load.go                        CSV readers, deduplication, graph assembly
  graph.go                       indexes and entity resolution
  query_match.go                 match search, head-to-head, derbies
  query_team.go                  club records and home/away splits
  query_competition.go           league tables and knockout brackets
  query_stats.go                 aggregates, leaderboards, season comparison
  query_player.go                FIFA player queries and the cross-file join
  rivalry.go                     the 20 traditional clássicos
internal/mcpsrv/               the MCP surface
  server.go                      tools, resources, prompts, schemas
  format.go                      the human-readable answer layouts
  samples.go                     the catalogue of sample questions
```

---

## Testing

```bash
go test ./...                                    # everything
go test ./internal/soccer -run TestFeature -v    # read the BDD scenarios
```

Three layers:

1. **Unit tests** for the normaliser, date parser and record arithmetic.
2. **BDD scenarios** (`internal/soccer/bdd_test.go`) written as
   Given/When/Then, following the Gherkin outline in the specification. Run
   with `-v` they read as a specification of the server's behaviour. They
   include a regression test that checks the computed champion of all twenty
   complete Série A seasons against the historical record.
3. **End-to-end MCP tests** (`internal/mcpsrv/server_test.go`) that connect a
   real MCP client to the server over an in-memory transport and exercise tool
   discovery, JSON Schema validation, structured output, resources, prompts,
   the error path and the specification's latency budgets. Every sample
   question in the catalogue is asserted to produce an answer.

Statement coverage: 87% of the query engine, 91% of the MCP layer.

---

## Known limitations

* **No goalscorers.** None of the six datasets records who scored. Top-scorer
  questions are answered at club level (goals for), never at player level.
* **The FIFA data is a FIFA 19 snapshot**, so it does not line up in time with
  the 2003–2023 match data, and only 15 Brazilian clubs are licensed. Players
  at unlicensed clubs appear under FIFA's placeholder names.
* **2023 Série A is three matches short** in the source, so it is reported as a
  partial table with no champion.
* **The Copa do Brasil file stops in 2021** and the Libertadores file in 2022;
  2022–2023 cup coverage comes only from the extended-statistics dataset, which
  carries no round labels.
* **Long-tail clubs may still split.** Reconciliation is exact for every club
  that has played in Série A and for the well-known lower-division sides, but a
  handful of the ~280 Copa do Brasil minnows that appear once or twice under
  idiosyncratic legal names may remain as separate nodes.

---

## Data sources

Kaggle data can't be downloaded without an account, so these (freely available
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

## Specification

The specification this server implements is in
[`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md) (also present
as `TASK.md`).
