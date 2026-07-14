# Brazilian Soccer MCP Server (Clojure)

An [MCP](https://modelcontextprotocol.io) server that turns the bundled Kaggle
datasets into a queryable knowledge base about Brazilian soccer — players,
teams, matches, competitions and statistics. It implements the specification in
[`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md) /
[`TASK.md`](TASK.md).

The server speaks **JSON-RPC 2.0 over stdio** and exposes a set of tools an LLM
client can call to answer natural-language questions.

## What was built

| File | Responsibility |
|------|----------------|
| `src/soccer/normalize.clj` | Team-name / date / number normalization (suffix, accent and date-format handling) |
| `src/soccer/data.clj` | Loads the six CSV files, unifies them into in-memory match & player records, and picks a single canonical source per season to avoid double-counting |
| `src/soccer/queries.clj` | Pure query / aggregation functions for every capability category |
| `src/soccer/format.clj` | Renders results as the human-readable text from the spec's examples |
| `src/soccer/mcp.clj` | The MCP JSON-RPC server: `initialize`, `tools/list`, `tools/call` |
| `src/soccer/main.clj` | Entry point (stdio server, or `--demo`) |
| `test/soccer/*_test.clj` | BDD (Given-When-Then) test suite over a small fixture |

Every source file opens with a detailed context block describing its purpose.

## Requirements

- A JVM (tested on OpenJDK 26)
- [Clojure CLI](https://clojure.org/guides/install_clojure) (tools.deps)

All library dependencies are pure-JVM (`data.csv`, `data.json`) — **no native
libraries and no external database** are required.

## Running

```bash
# Start the MCP stdio server (waits for JSON-RPC on stdin)
clojure -M -m soccer.main

# Print answers to a set of sample questions from the spec
clojure -M -m soccer.main --demo

# Run the BDD test suite
clojure -M:test
```

### Using it as an MCP server

Register it with any MCP-capable client, e.g. a `claude_desktop_config.json`
entry:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "clojure",
      "args": ["-M", "-m", "soccer.main"],
      "cwd": "/absolute/path/to/this/repo"
    }
  }
}
```

Diagnostics go to **stderr**; **stdout** carries only JSON-RPC, keeping the
channel clean.

## Tools

| Tool | What it answers |
|------|-----------------|
| `search_matches` | Matches by team / second team / competition / season / date range |
| `head_to_head` | Head-to-head record between two teams |
| `team_stats` | A team's W/D/L, goals, points and win rate (filter by season/competition/venue) |
| `standings` | Final league table for a competition + season, computed from results |
| `league_stats` | Average goals, home/away win rate and draw rate for a competition |
| `biggest_wins` | Largest-margin victories |
| `search_players` | FIFA players by name / nationality / club / position / rating |
| `season_summary` | Compare several seasons of a competition |

Example call and reply:

```jsonc
// → request on stdin
{"jsonrpc":"2.0","id":3,"method":"tools/call",
 "params":{"name":"standings","arguments":{"competition":"Brasileirão Série A","season":2019}}}

// ← response on stdout (text content), top of the table:
// 1. Flamengo-RJ   90 pts (28W 6D 4L) ... Champion
// 2. Palmeiras-SP  74 pts (21W 11D 6L)
// 3. Santos-SP     74 pts (22W 8D 8L)
```

## Data handling notes

The spec calls out several data-quality challenges, addressed as follows:

- **Team-name variations** — names are tidied to a display form that *keeps* the
  state/country suffix (so `Atlético-MG` ≠ `Atlético-PR`), while a bare query
  like `Flamengo` still matches `Flamengo-RJ` via accent-folded substring keys.
- **Date formats** — ISO (`2023-09-24`), datetime (`2012-05-19 18:30:00`) and
  Brazilian (`29/03/2003`) are all normalized to ISO `yyyy-MM-dd`.
- **Character encoding** — files are read as UTF-8 and accents are folded only
  for matching keys, never for display.
- **Overlapping sources** — the Brasileirão appears in three files with
  inconsistent club spellings. Rather than fragile row-level de-duplication, the
  loader selects a single highest-priority source per `(competition, season)`,
  yielding exactly one clean copy of each season (e.g. 380 Série A matches in
  2019, producing the correct `Flamengo 90 pts` champion table). BR-Football
  still extends coverage to seasons/competitions the dedicated files lack
  (Série B/C, more recent years).

### Dataset coverage caveat

The bundled FIFA player dataset is the FIFA 19 export. For licensing reasons it
omits several major Brazilian clubs (e.g. Flamengo, Palmeiras, Corinthians) and
the players who were at them, so a search such as *"players at Flamengo"* may
return nothing even though the query is working. Clubs that **are** present
(Santos, Grêmio, Internacional, Cruzeiro, Fluminense, …) and Brazilian players
at European clubs (Neymar, Casemiro, Gabriel Jesus, …) are fully searchable.

## Data Sources

The data is bundled under `data/kaggle/`:

| File | Source | License |
|------|--------|---------|
| `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv` | [jogos-do-campeonato-brasileiro](https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro) | CC BY 4.0 |
| `BR-Football-Dataset.csv` | [brazilian-football-matches](https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches) | CC0 Public Domain |
| `novo_campeonato_brasileiro.csv` | [campeonato-brasileiro-2003-a-2019](https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019) | CC BY 4.0 |
| `fifa_data.csv` | [fifa-players-data](https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data) | Apache 2.0 |

## Testing

The suite uses BDD Given-When-Then scenarios (`clojure.test`) over a small,
deterministic fixture so assertions have known exact values:

```bash
clojure -M:test
# Ran 18 tests containing 68 assertions. 0 failures, 0 errors.
```

It covers normalization, every query category, and the MCP JSON-RPC surface.
