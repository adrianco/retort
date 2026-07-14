# Brazilian Soccer MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) server that exposes a
knowledge graph over Brazilian soccer data (matches, teams, players, competitions
and statistics) so an LLM can answer natural-language questions about Brazilian
football. Implemented in **Java 21** with no MCP SDK dependency — the JSON-RPC 2.0
protocol is spoken directly over stdio.

This implements the specification in
[`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md) /
[`TASK.md`](TASK.md).

---

## What was built

An in-memory query engine over the six provided Kaggle CSV datasets, exposed as a
set of MCP tools. The server loads all data at startup (~40k rows in well under a
second) and answers every query category in the spec:

| # | Category | MCP tools |
|---|----------|-----------|
| 1 | Match queries | `search_matches` |
| 2 | Team queries | `team_record`, `head_to_head` |
| 3 | Player queries | `search_players` |
| 4 | Competition queries | `standings` |
| 5 | Statistical analysis | `league_statistics`, `biggest_wins` |
| – | Introspection | `data_summary` |

### Example: 2019 Brasileirão standings (calculated from match results)

```
Pos  Team                         P   W   D   L   GF   GA   GD  Pts
1    Flamengo-RJ                 38  28   6   4   86   37   49   90
2    Santos-SP                   38  22   8   8   60   33   27   74
3    Palmeiras-SP                38  21  11   6   61   32   29   74
...
Champion: Flamengo-RJ
```

This matches the real 2019 Campeonato Brasileiro result, computed purely from the
match data.

---

## Build & run

Requires JDK 21+ and Maven.

```bash
mvn package                                   # compile, test, build fat JAR
java -jar target/brazilian-soccer-mcp.jar     # serve MCP over stdio
```

The data directory is resolved from (in order): the first CLI argument, the
`SOCCER_DATA_DIR` environment variable, or the default `data/kaggle`.

Diagnostics are written to **stderr**; **stdout** carries only JSON-RPC frames, so
the binary can be wired straight into an MCP client.

### Connecting from an MCP client (e.g. Claude Desktop)

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "java",
      "args": ["-jar", "/absolute/path/to/target/brazilian-soccer-mcp.jar"]
    }
  }
}
```

### Quick manual check

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"standings","arguments":{"competition":"Brasileirao","season":2019}}}' \
  | java -jar target/brazilian-soccer-mcp.jar
```

---

## Tools

| Tool | Key arguments | Answers questions like |
|------|---------------|------------------------|
| `search_matches` | `team`, `opponent`, `competition`, `season`, `start_date`, `end_date`, `venue`, `limit` | "Show me all Flamengo vs Fluminense matches", "What matches did Palmeiras play in 2019?" |
| `head_to_head` | `team1`, `team2` | "Compare Palmeiras and Santos head-to-head" |
| `team_record` | `team`, `season`, `competition`, `venue` | "What is Corinthians' home record in 2022?" |
| `search_players` | `name`, `nationality`, `club`, `position`, `min_overall`, `sort_by`, `limit` | "Find all Brazilian players", "Who is Neymar?" |
| `standings` | `competition`, `season` | "Who won the 2019 Brasileirão?" |
| `league_statistics` | `competition`, `season` | "What's the average goals per match?" |
| `biggest_wins` | `competition`, `season`, `limit` | "Show me the biggest wins in the dataset" |
| `data_summary` | – | "What data is available?" |

---

## Architecture

```
com.brasilsoccer.mcp
├── Main                     entry point: resolve data dir, load, serve stdio
├── model/                   immutable records
│   ├── Match                unified match across all datasets (+ base/full keys)
│   └── Player               FIFA player subset
├── util/TeamNames           name normalisation (accents, state suffixes)
├── data/
│   ├── DataLoader           CSV → model (per-file column/date/encoding handling)
│   └── KnowledgeBase        in-memory query engine (all 5 query categories)
├── query/
│   ├── MatchQuery           filter builder for match search
│   ├── Results              value objects returned by queries
│   └── ResponseFormatter    renders results as readable text
└── mcp/
    ├── McpServer            JSON-RPC 2.0 dispatch + stdio loop
    └── ToolSchemas          tool definitions / JSON schemas for tools/list
```

Every source file opens with a detailed context-block comment describing its role.

### Key design decisions

These come straight from the *Data Quality Notes* in the spec:

- **Team-name normalisation with a twist.** Names appear as `Palmeiras-SP`,
  `Palmeiras`, `São Paulo`, `Nacional (URU)`, etc. The normaliser produces two
  keys per team:
  - a **base key** (state suffix stripped, accents folded) so `Palmeiras-SP`,
    `Palmeiras` and `palmeiras` all match — used for search, head-to-head and
    records;
  - a **full key** (state suffix kept) so that clubs sharing a base name stay
    distinct. This matters: `Atlético-MG` and `Atlético-PR` would otherwise merge
    and corrupt the league table. Standings group on the full key.
- **Overlapping datasets de-duplicated at load.** Serie A 2014–2019 appears in
  three different files with inconsistent spellings, which makes row-level dedup
  unreliable. Instead, each `(competition, season)` group is collapsed to a single
  **authoritative source** (chosen by a curated priority: dedicated league files
  over the merged extract), so every query sees one consistent, non-double-counted
  view. Coverage still spans **2003–2023** (e.g. 2003–2011 from the historical
  file, 2023 from the extended-stats file).
- **Multiple date formats** (`2023-09-24`, `2012-05-19 18:30:00`, `29/03/2003`)
  and **UTF-8 Portuguese text** are handled in the loader.
- **Robustness:** rows with unparseable scores are skipped rather than aborting
  the load.

---

## Testing

BDD-style **Given / When / Then** tests written with JUnit 5 (`@DisplayName`
spells out each scenario), covering all five query categories plus the protocol
layer:

```bash
mvn test
```

| Test | Covers |
|------|--------|
| `TeamNamesTest` | normalisation rules (base/full keys, accents) |
| `DataLoadingTest` | all six datasets load; competitions & seasons present |
| `MatchQueryTest` | match search by team / pair / competition / season / venue |
| `TeamQueryTest` | records, home/away splits, head-to-head consistency |
| `PlayerQueryTest` | search by name / nationality / club / rating, sorting |
| `CompetitionStandingsTest` | calculated tables (2019 ground truth, club distinctness) |
| `StatisticsTest` | average goals, result-rate sums, biggest-wins ordering |
| `McpServerTest` | initialize, tools/list, tools/call, notifications, errors |

Assertions mix structural invariants (W+D+L = games played, points = 3·W+D,
rates sum to 100%) with historically verifiable facts (2019 Brasileirão won by
Flamengo on 90 points; Neymar is a 92-rated Brazilian).

---

## Data sources

Kaggle data can't be downloaded without an account, so these freely-available
datasets (used with attribution) are included under `data/kaggle/`:

| File | Source | License |
|------|--------|---------|
| `Brasileirao_Matches.csv` | [ricardomattos05/jogos-do-campeonato-brasileiro](https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro) | CC BY 4.0 |
| `Brazilian_Cup_Matches.csv` | same as above | CC BY 4.0 |
| `Libertadores_Matches.csv` | same as above | CC BY 4.0 |
| `BR-Football-Dataset.csv` | [cuecacuela/brazilian-football-matches](https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches) | CC0 Public Domain |
| `novo_campeonato_brasileiro.csv` | [macedojleo/campeonato-brasileiro-2003-a-2019](https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019) | CC BY 4.0 |
| `fifa_data.csv` | [youssefelbadry10/fifa-players-data](https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data) | Apache 2.0 |

> Note: the FIFA dataset (FIFA 19 era) only licensed some Brazilian clubs — e.g.
> Grêmio, Santos and Botafogo are present, while Flamengo and Palmeiras are not.
> Player-by-club queries reflect exactly what the dataset contains.
