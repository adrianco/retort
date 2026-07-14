# Brazilian Soccer MCP Server (Clojure)

An [MCP](https://modelcontextprotocol.io) server that answers natural-language
questions about Brazilian soccer — matches, teams, players, competitions and
aggregate statistics — over the bundled Kaggle datasets. It speaks JSON-RPC 2.0
over stdio and exposes six tools an LLM can call.

Built test-first; see [`test/`](test/brazilian_soccer). Implements the
specification in [`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md)
/ [`TASK.md`](TASK.md).

## Quick start

Requires a JDK and the [Clojure CLI](https://clojure.org/guides/install_clojure).

```bash
# run the test suite
clojure -M:test

# start the MCP server (reads JSON-RPC from stdin, writes to stdout)
clojure -M:run
# optional: point at a different data directory
clojure -M:run /path/to/csv/dir      # default: data/kaggle
```

Smoke-test it from the shell:

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"standings","arguments":{"competition":"Brasileirão","season":2019}}}' \
  | clojure -M:run
```

```
2019 Brasileirão Final Standings (calculated from matches):
1. Flamengo - 90 pts (28W, 6D, 4L)
2. Palmeiras - 74 pts (21W, 11D, 6L)
3. Santos - 74 pts (22W, 8D, 8L)
...
```

### Connecting from an MCP client

Add to your client's MCP server config (e.g. Claude Desktop's
`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "clojure",
      "args": ["-M:run"],
      "cwd": "/absolute/path/to/this/repo"
    }
  }
}
```

## Tools

| Tool | Purpose | Key arguments |
|------|---------|---------------|
| `find_matches`   | Find matches by team, opponent, competition, season, venue or date range | `team`, `opponent`, `competition`, `season`, `venue` (`home`/`away`), `from`, `to` (`YYYY-MM-DD`), `limit` |
| `head_to_head`   | Wins/draws/goals between two teams | `team_a`, `team_b` |
| `team_record`    | W/D/L record, goals and points for a team | `team`, `competition`, `season`, `venue` |
| `standings`      | League table calculated from match results | `competition`, `season` |
| `search_players` | Search FIFA players, sorted by overall rating | `name`, `nationality`, `club`, `position`, `limit` |
| `statistics`     | Avg goals/match, home-win rate, biggest wins | `competition`, `season` (both optional) |

### Example questions these answer

- *"Who won the 2019 Brasileirão?"* → `standings` (Flamengo, 90 pts)
- *"Compare Palmeiras and Santos head-to-head"* → `head_to_head`
- *"What is Corinthians' home record in 2022?"* → `team_record` with `venue: home`
- *"Show me all Flamengo vs Fluminense matches"* → `find_matches`
- *"Who are the top Brazilian players?"* → `search_players` with `nationality: Brazil`
- *"What's the average goals per match in the Brasileirão?"* → `statistics`

## Architecture

```
src/brazilian_soccer/
  normalize.clj  — team-name / date / number normalization (the data-quality core)
  data.clj       — load & unify the 6 CSVs into one match schema + players
  queries.clj    — pure query/aggregation engine over the in-memory db
  format.clj     — render results as the human-readable answers in the spec
  mcp.clj        — JSON-RPC 2.0 dispatch + stdio loop (entry point)
```

The flow is `data → queries → format`, wired together by `mcp`. Everything but
the stdio loop is a pure function, which is why the whole surface is unit-tested
(`handle-request` is tested directly without any I/O).

### Handling the data-quality challenges

The datasets are inconsistent in exactly the ways the spec calls out, and the
`normalize` namespace addresses each:

- **Team-name variations.** `"Palmeiras-SP"`, `"Palmeiras"` and
  `"Nacional (URU)"` are reduced to a canonical key for matching. State suffixes
  matter, though: `"Atlético-MG"` and `"Atlético-GO"` are *different clubs*, so
  there are two keys — a loose, suffix-stripped key for user queries (so typing
  "Flamengo" finds "Flamengo-RJ"), and a strict, suffix-preserving key used when
  building standings. The known `Athletico`/`Atlético` spelling split is folded.
- **Date formats.** ISO (`2023-09-24`), ISO-with-time (`2012-05-19 18:30:00`)
  and Brazilian (`29/03/2003`) all parse to `java.time.LocalDate`.
- **Numbers.** Goal columns that look like floats (`2.0`) parse to integers.
- **Encoding.** UTF-8 throughout; accents are preserved for display and folded
  for matching.

### Avoiding double-counting

Several files overlap — Brasileirão seasons 2012-2019 appear in both
`novo_campeonato_brasileiro.csv` and `Brasileirao_Matches.csv`; Copa do Brasil
appears in both `Brazilian_Cup_Matches.csv` and `BR-Football-Dataset.csv`. Naive
concatenation would double every overlapping match and inflate every standings
table and average. Because the inconsistent naming makes fuzzy per-fixture
matching unreliable, the loader instead picks, for each `(competition, season)`,
the single richest source file and drops the rest (`data/select-best-source`).
This yields exactly 380 matches for a 20-team Brasileirão season and the correct
final tables (e.g. Flamengo's real 90-point 2019 title).

## Known limitations

- The bundled **FIFA player dataset is the 2019 edition**, dominated by European
  clubs. ~827 Brazilian-nationality players are present (Neymar, Casemiro,
  Coutinho, …) but most Brazilian *domestic* clubs are not, so
  "players at Flamengo" can legitimately return nothing.
- A long tail of rare club-name spelling variants (e.g. *Vasco* vs
  *Vasco da Gama* across files) can still split a row or two in standings drawn
  from different seasons. The major clubs are handled correctly.
- Standings/records reflect only the matches in the provided datasets.

## Data Sources

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
