# Brazilian Soccer MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) server, written in
**Clojure**, that exposes a queryable knowledge base of Brazilian soccer built
from six bundled Kaggle datasets. Connect it to an MCP-capable LLM client (e.g.
Claude Desktop) to answer natural-language questions about matches, teams,
players, competitions and statistics.

The full specification is in [`TASK.md`](TASK.md) /
[`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md).

## Quick start

Requires the Clojure CLI (`clojure`) and a JDK (11+).

```bash
# Run the MCP server (speaks JSON-RPC 2.0 over stdio)
clojure -M -m brazilian-soccer.main

# Run the test suite (44 BDD scenarios)
clojure -M:test
```

On startup the server loads every dataset into memory and prints a readiness
line to **stderr** (stdout is reserved for the protocol):

```
brazilian-soccer-mcp: loaded 21647 matches and 18207 players. Ready on stdio.
```

### Use from an MCP client

Add to your client's MCP server configuration (Claude Desktop example):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "clojure",
      "args": ["-M", "-m", "brazilian-soccer.main"],
      "cwd": "/absolute/path/to/this/repo"
    }
  }
}
```

### Try it without a client

Pipe newline-delimited JSON-RPC requests to stdin:

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"champion","arguments":{"season":2019}}}' \
  | clojure -M -m brazilian-soccer.main
```

## Tools

The server advertises 10 tools via `tools/list`. Each returns a formatted text
block via `tools/call`.

| Tool | Purpose | Key arguments |
|------|---------|---------------|
| `find_matches` | Find matches by team / opponent / competition / season / date range | `team`, `home`, `away`, `opponent`, `competition`, `season`, `from`, `to`, `limit` |
| `matches_between` | All games between two teams + head-to-head summary | `team_a`, `team_b`, `limit` |
| `head_to_head` | Win/draw/goal record between two teams | `team_a`, `team_b` |
| `team_record` | W/D/L and goals for a team (overall / home / away) | `team`, `venue`, `season`, `competition` |
| `find_players` | Search FIFA players by name/nationality/club/position/rating | `name`, `nationality`, `club`, `position`, `min_overall`, `limit` |
| `top_players` | Highest-rated players, optionally by nationality | `nationality`, `limit` |
| `standings` | League table computed from results (3 pts win / 1 draw) | `season`, `competition`, `limit` |
| `champion` | Champion of a competition/season from standings | `season`, `competition` |
| `statistics` | Avg goals/match, home-win rate, biggest victories | `competition`, `season` |
| `list_teams` | Distinct team names, optionally per competition | `competition` |

Example — *"Who won the 2019 Brasileirão?"* → `champion {season: 2019}`:

```
Brasileirão 2019 champion (computed from 455 matches):
Flamengo — 90 pts (28W 6D 4L, GD +49)
```

## How it works

```
src/brazilian_soccer/
  normalize.clj  team-name cleaning, accent folding, fuzzy & identity keys
  data.clj       CSV loading, field parsing, cross-file de-duplication
  queries.clj    pure query/statistics functions over the normalised data
  format.clj     render results as LLM-friendly text
  tools.clj      MCP tool catalogue (JSON-Schema) + dispatch
  mcp.clj        JSON-RPC 2.0 stdio transport / protocol lifecycle
  main.clj       entry point
test/brazilian_soccer/
  fixtures.clj + *_test.clj   Given/When/Then BDD scenarios
```

All six CSVs are normalised into one uniform match collection plus a player
collection (see the schema docs at the top of `data.clj`). Queries are pure
functions of the data, so they are unit-testable without disk or network access.

### Handling messy data

The datasets are inconsistent, and the code addresses each issue called out in
the spec:

- **Team-name variations** — state suffixes (`Palmeiras-SP`), country codes
  (`Nacional (URU)`), spaced suffixes (`América - MG`) and descriptors are
  stripped for a human display name; a separate accent-folded *match key* powers
  fuzzy search (so `"Flamengo"` matches `"Flamengo-RJ"`).
- **Same name, different club** — a canonical *identity key* combines the base
  name with the dataset's dedicated state column, keeping **Atlético-MG**,
  **Atlético-GO** and **Athletico-PR** distinct in standings.
- **Date formats** — ISO, ISO+time and Brazilian `DD/MM/YYYY` are all normalised
  to `yyyy-MM-dd`.
- **UTF-8 / accents** — all files are read as UTF-8 and protocol output preserves
  Portuguese characters.
- **Overlapping sources** — the Brasileirão appears in three files; identical
  games (same date, teams and score) are de-duplicated on load.

### Known data-quality limitations

These are inherent to the source data, not the server:

- The Kaggle Brasileirão files use **different naming conventions** (one adds a
  state suffix, one does not), so a small number of games whose dates or scores
  differ slightly between files are not merged. Computed point totals can
  therefore be marginally higher than the official record, though champions and
  rankings are correct.
- `BR-Football-Dataset.csv` labels its top flight `Serie A` (not "Brasileirão")
  and uses long club names, so it forms a separate, non-merged view used by the
  whole-dataset statistics rather than by season standings.
- `fifa_data.csv` is a FIFA-19 snapshot: it does **not** include every Brazilian
  club (e.g. Flamengo, Palmeiras were unlicensed) and uses placeholder names for
  some unlicensed players. Player queries reflect exactly what that file
  contains.

## Testing

BDD (Given/When/Then) scenarios with `clojure.test`, covering normalisation,
parsing/loading, every query family, the tool-dispatch layer and the JSON-RPC
protocol (including an end-to-end stdio round-trip):

```bash
clojure -M:test
# Ran 44 tests containing 133 assertions. 0 failures, 0 errors.
```

## Data sources

Kaggle data can't be downloaded without an account, so these (freely available
with attribution) datasets have been downloaded for use here:

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
