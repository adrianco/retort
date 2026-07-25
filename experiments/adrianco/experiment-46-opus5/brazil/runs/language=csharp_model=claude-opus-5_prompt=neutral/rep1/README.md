# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server that answers natural-language questions about Brazilian
football. It builds an in-memory knowledge graph from the six bundled Kaggle CSV files and exposes
16 tools an LLM can call.

The specification this implements is in [TASK.md](TASK.md) (a copy of
`brazilian-soccer-mcp-guide.md`).

```
16,818 matches   409 clubs   18,207 players   built in ~0.4 s
```

| Competition | Matches | Seasons |
|---|---|---|
| Campeonato Brasileiro Série A | 8,404 | 2003-2023 |
| Campeonato Brasileiro Série B | 3,677 | 2014-2023 |
| Campeonato Brasileiro Série C | 1,807 | 2014-2023 |
| Copa do Brasil | 1,676 | 2012-2023 |
| Copa Libertadores | 1,254 | 2013-2022 |

## Quick start

```bash
dotnet build                                          # build everything
dotnet test                                           # 250 tests, ~1 s
dotnet run --project src/BrazilianSoccer.McpServer -- --check   # print what was loaded
dotnet run --project src/BrazilianSoccer.McpServer              # speak MCP over stdio
```

### Connect it to an MCP host

```jsonc
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "dotnet",
      "args": ["run", "--project", "/abs/path/to/src/BrazilianSoccer.McpServer"],
      "env": { "BRAZILIAN_SOCCER_DATA": "/abs/path/to/data/kaggle" }
    }
  }
}
```

`BRAZILIAN_SOCCER_DATA` is optional: the server also walks up from its working directory looking for
`data/kaggle`. A `--data <dir>` command-line option does the same thing.

For Claude Code: `claude mcp add brazilian-soccer -- dotnet run --project $(pwd)/src/BrazilianSoccer.McpServer`

## Tools

| Tool | Answers questions like |
|---|---|
| `list_datasets` | "What data do you have?" |
| `list_teams` | "What clubs are in the graph?" |
| `search_matches` | "Show me all Flamengo vs Fluminense matches", "Find all Copa do Brasil finals" |
| `head_to_head` | "When did Flamengo last play Corinthians?", "Compare Palmeiras and Santos" |
| `biggest_wins` | "Show me the biggest wins in the dataset" |
| `team_stats` | "What is Corinthians' home record in 2022?" |
| `team_profile` | "What competitions has Palmeiras played in?" |
| `season_standings` | "Who won the 2019 Brasileirão?", "Which teams were relegated in 2020?" |
| `competition_bracket` | "Show the 2018 Copa Libertadores bracket" |
| `competition_stats` | "What's the average goals per match in the Brasileirão?" |
| `team_rankings` | "Which team scored the most goals in Serie A 2023?", "Best away record?" |
| `compare_seasons` | "Compare the 2018 and 2019 seasons" |
| `search_players` | "Find all Brazilian players", "Show me all forwards from Cruzeiro" |
| `player_profile` | "Who is Gabriel Jesus?" |
| `club_squad` | "Who are the highest-rated players at Grêmio?" |
| `brazilian_club_squads` | "Who are the top Brazilian players?" |

Two prompts (`scout_club`, `season_review`) chain several tools into a report.

Example output:

```
2019 Campeonato Brasileiro Série A - table calculated from 380 matches

Pos  Team                      Pl   W   D   L    GF   GA   GD  Pts
  1  Flamengo                  38  28   6   4    86   37   49   90
  2  Santos                    38  22   8   8    60   33   27   74
  3  Palmeiras                 38  21  11   6    61   32   29   74
  ...
 20  Avaí                      38   3  11  24    18   62  -44   20

Champion: Flamengo (90 pts)
Relegated (bottom four): Cruzeiro (36 pts), CSA (32 pts), Chapecoense (32 pts), Avaí (20 pts)
```

That table matches the official 2019 Brasileirão exactly, including the tie-break that puts Santos
above Palmeiras on wins. Nothing is hard-coded: every standing, record and average is calculated
from the match rows.

## How it works

```
data/kaggle/*.csv
      |  CsvReader        RFC 4180, UTF-8, streaming
      |  TeamRegistry     every spelling of a club -> one node
      |  DataLoader       merge overlapping sources into one match per fixture
      v
KnowledgeGraph            clubs + players + competitions joined by match edges
      |  Query services   MatchQuery / TeamStats / Standings / PlayerQuery / Statistics
      v
MCP tools (stdio)
```

* `src/BrazilianSoccer.Core` - data loading, the graph and all query logic. No MCP dependency.
* `src/BrazilianSoccer.McpServer` - the 16 tools and the stdio host.
* `tests/BrazilianSoccer.Tests` - BDD feature files, unit tests, protocol tests, benchmarks.

The graph is built once at start-up and is immutable afterwards, so queries never touch the disk.

### Data problems that had to be solved

**One club, many spellings.** The sources write the same club as `Palmeiras-SP`, `Palmeiras`,
`Palmeiras - SP`; as `Sport Club do Recife`, `Sport-PE`, `Sport Recife`; as `Athletico Paranaense`,
`Atletico-PR`, `Athletico`. Names are folded (accents removed, club-type words such as
*Esporte Clube* and connectors such as *do/da* dropped) and matched against a curated registry of
223 clubs. Clubs that merely share a name stay apart: `Botafogo` is Botafogo-RJ, `Botafogo - PB` is
not, and `Fluminense PI` is not Fluminense.

**Overlapping sources.** The three Brasileirão files cover 2003-2019, 2012-2022 and 2014-2023, so
7,133 rows are re-descriptions of 4,956 matches already read from an earlier file. A fixture is
recognised across files by competition, season, ground and a date window; the first source owns it
and later ones only fill gaps. That is how the
2022 season gets its scores (the Brasileirão file stores them as `NA`) and how 2014-2023 matches
gain shots, corners and attacks. A postponed match recorded on two different dates is still merged,
because a league pairing happens once per ground per season.

**An unreliable state column.** The historical file tags Bahia's state as `BH` and some Vitória rows
as `ES`. A state written *inside* a name is trusted; a state from a separate column is only a hint,
overridden when the name alone identifies a known club.

**Missing scores.** The Brasileirão file stores 82 scores as `NA` and the Libertadores file has two
`-` rows. Merging recovers all but one of them. Matches that still have no score are never counted
as draws: records, tables and averages skip them, and the tools report how many were skipped.

**Season boundaries.** The extended dataset has no season column, and Brazilian seasons spill into
the next January. League fixtures played before April are assigned to the previous season.

**Unicode.** `InvariantGlobalization` is explicitly off. In invariant mode `string.Normalize` is a
no-op, which silently breaks accent folding and split *Grêmio* from *Gremio*.

### Known data limitations

These are properties of the sources, and the tools state them rather than hiding them:

* **2023 Série A is 3 matches short**, so no champion or relegation is declared for it. Incomplete
  seasons still produce a table.
* **The player data is a FIFA 19 snapshot.** It has ratings and attributes but no goals or
  appearances, and it licenses only 15 Brazilian clubs - Flamengo, Palmeiras, Corinthians and
  São Paulo have no players in it even though their matches are complete. Asking for their squad
  returns an explanation, not an empty list.
* **Top scorers cannot be answered.** No source lists goal scorers; the tools do not pretend
  otherwise.
* **A handful of source rows are mislabelled** (a Campeonato Brasiliense match filed under Série A).
  Clubs with a couple of fixtures in a 38-round league are dropped from that table and listed in a
  note.
* **2009 Botafogo-Flamengo appears twice with Botafogo at home**, three months apart with different
  scores. Both are kept: they are two real matches the source recorded that way.

## Tests

```bash
dotnet test                                        # everything
dotnet test --filter FullyQualifiedName~FeatureTests   # just the BDD scenarios
```

250 tests in five groups:

* **BDD scenarios** (`tests/.../Features/*.feature`) - the specification's Gherkin, executed. A
  small Gherkin parser and step runner (`Bdd/`) turns each `Scenario` and each row of a
  `Scenario Outline` into its own xUnit test, so a failure names the behaviour and the step.
  Every `When` goes through the MCP tool surface an LLM would call.
* **Unit tests** - name folding, the club registry, the CSV reader, date formats, and graph
  integrity. Several assert against real-world results: the champions and points of nine
  Brasileirão seasons, the 2019 tie-break, and both relegation quartets. Getting those right by
  accident after a bad merge is not plausible, so they are the strongest end-to-end check available.
* **Sample questions** - the specification asks for 20 answerable questions; 27 are covered, each
  with the tool call and the fragments its answer must contain. The full answers are written to the
  test output, so the run doubles as a demo transcript.
* **Protocol tests** - launch the server as a child process and drive it with an MCP client over
  stdio: tool discovery, JSON schemas, argument validation, prompts, one call per tool, and the
  `--check` command line including its behaviour when the data directory is missing.
* **Benchmarks** - assert the specification's budgets. Simple lookups land at 0.5-30 ms against a
  2 s budget; aggregate queries at 1-8 ms against 5 s.

## Data sources

Kaggle data can't be downloaded without an account, so these (freely available with attribution)
data sets have been downloaded for use here:

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
