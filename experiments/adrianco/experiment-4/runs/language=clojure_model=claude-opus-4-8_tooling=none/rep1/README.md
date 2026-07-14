# Brazilian Soccer MCP Server (Clojure)

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server that
exposes a knowledge graph of Brazilian soccer data as a set of natural-language
query tools. An LLM host (e.g. Claude Desktop) connects over the MCP **stdio**
transport and can ask about matches, teams, players, competitions and
statistics, with answers computed from six pre-downloaded Kaggle datasets.

Implemented in **Clojure** (Clojure CLI / `deps.edn`), tested with a
behaviour-driven (Given-When-Then) `clojure.test` suite.

---

## Quick start

```bash
# Run the test suite (BDD scenarios)
clojure -M:test

# Start the MCP server on stdio (reads/writes newline-delimited JSON-RPC)
clojure -M:run

# Use a custom data directory (defaults to data/kaggle)
clojure -M:run /path/to/data
#   or:  BRAZIL_SOCCER_DATA=/path/to/data clojure -M:run
```

Requires a JDK and the Clojure CLI. Dependencies (`data.csv`, `cheshire`) are
fetched automatically on first run.

### Talking to it by hand

The server speaks JSON-RPC 2.0, one message per line. Example session:

```bash
printf '%s\n%s\n' \
 '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
 '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"standings","arguments":{"season":2019,"top":5}}}' \
 | clojure -M:run
```

```
Brasileirão Série A 2019 Final Standings (calculated from matches):
1. Flamengo - 90 pts (28W, 6D, 4L)
2. Palmeiras - 74 pts (21W, 11D, 6L)
3. Santos - 74 pts (22W, 8D, 8L)
4. Grêmio - 65 pts (19W, 8D, 11L)
5. Atlético - 64 pts (18W, 10D, 10L)
```

### Registering with an MCP client

Add to your client's MCP server config (Claude Desktop `claude_desktop_config.json`):

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

---

## MCP tools

The server advertises the following tools via `tools/list`. Each returns a
human-readable text block suitable for an LLM to relay.

| Tool | Purpose | Key arguments |
|------|---------|---------------|
| `search_matches` | Find matches by team / opponent / competition / season / date range | `team, side, opponent, competition, season, date_from, date_to, limit` |
| `team_stats` | W/D/L, goals, win-rate for a team | `team, season, competition, venue` |
| `head_to_head` | Head-to-head record between two teams | `team1, team2, show` |
| `search_players` | FIFA players by name / nationality / club / position / rating | `name, nationality, club, position, min_overall, limit` |
| `club_roster` | A club's squad with size and average rating | `club` |
| `standings` | Computed league table (3pts win / 1pt draw) | `competition, season, top` |
| `champion` | The calculated champion of a season | `competition, season` |
| `competition_stats` | Match count, total/avg goals, home/away win rates | `competition, season` |
| `biggest_wins` | Matches with the largest goal margin | `competition, season, limit` |
| `best_record` | Teams ranked by win rate (home/away/all) | `competition, season, venue, limit` |
| `list_competitions` | All competitions in the dataset | – |
| `list_seasons` | Seasons available (optionally per competition) | `competition` |

### Example questions these answer

- *"Show me all Flamengo vs Fluminense matches"* → `search_matches`
- *"What is Corinthians' home record in 2022?"* → `team_stats`
- *"Compare Palmeiras and Santos head-to-head"* → `head_to_head`
- *"Who are the top Brazilian players?"* → `search_players {nationality: Brazil}`
- *"Which players play for Santos?"* → `club_roster`
- *"Who won the 2019 Brasileirão?"* → `champion` / `standings`
- *"What's the average goals per match in the Brasileirão?"* → `competition_stats`
- *"Show me the biggest wins in the dataset"* → `biggest_wins`
- *"Which team has the best home record?"* → `best_record`

---

## Architecture

```
src/brazilian_soccer/
  normalize.clj  Text & value normalization (team-name keys, dates, numbers)
  data.clj       CSV loading -> unified in-memory knowledge graph
  query.clj      Pure query functions over the graph (no IO/formatting)
  format.clj     Renders query results into readable answer blocks
  mcp.clj        MCP / JSON-RPC 2.0 protocol layer + tool definitions
  main.clj       Entry point: load data, serve on stdio
test/brazilian_soccer/
  fixtures.clj   Shared (memoized) loaded database
  normalize_test.clj, query_test.clj, mcp_test.clj   BDD scenarios
```

**Knowledge graph.** Rather than depend on an external graph database (e.g.
Neo4j), the data is modelled as an in-memory property graph so the server and
its full test suite run with **zero external infrastructure**. The nodes are
`Team`, `Match`, `Competition` and `Player`; relationships are expressed through
shared canonical keys (a match's `home-key`/`away-key` link to `Team` nodes; a
player's `club-key` links to a club). Every match from every file is normalized
into one uniform schema, so queries never care which file a row came from.

### Handling the messy data

The datasets disagree with each other in exactly the ways the specification
warns about, and reconciling them is the core engineering problem:

- **Team-name variations** — `Palmeiras-SP` vs `Palmeiras`, `Grêmio` vs
  `Gremio`, `Nacional (URU)`. The canonical key folds accents, lower-cases and
  normalizes punctuation. Crucially it **keeps the state/country suffix**,
  because several distinct clubs share a base name and are only told apart by it
  (Atlético-**MG** / -**PR** / -**GO**, América-**MG** / -**RN**,
  Botafogo-**RJ** / -**PB**). The query layer reconciles a suffix-less query
  (`"Palmeiras"`) with a suffixed key (`palmeiras sp`) via substring matching.
  Display names are cleaned (suffix stripped) and the most accented spelling is
  preferred (`Grêmio`, `São Paulo`).
- **Overlapping sources** — the same league season appears in up to three files.
  Naively merging them triple-counts every game and inflates standings. The
  loader therefore uses **one authoritative source per competition**: the modern
  `Brasileirao_Matches.csv` for Série A, the historical file only for the earlier
  seasons it alone covers, the dedicated cup/Libertadores files for those, and
  `BR-Football-Dataset.csv` only for Série B/C (its sole-source data). The result
  is a clean, non-overlapping graph — the 2019 Série A is exactly 20 teams ×
  38 games, with Flamengo champions on 90 points, matching reality.
- **Date formats** — ISO, ISO+time and Brazilian `DD/MM/YYYY` are all normalized
  to ISO `YYYY-MM-DD`.
- **Character encoding** — files are read as UTF-8 (with BOM stripping) so
  accents and cedillas are preserved.
- **Club look-alikes** — player-club search uses exact-match-first semantics so
  *"Santos"* returns Santos FC, not the unrelated *"Santos Laguna"*.

### Data coverage after normalization

| Competition | Source | Notes |
|-------------|--------|-------|
| Brasileirão Série A | `Brasileirao_Matches.csv` + `novo_campeonato_brasileiro.csv` | modern 2012–2023 + historical 2003–2011 |
| Copa do Brasil | `Brazilian_Cup_Matches.csv` | |
| Copa Libertadores | `Libertadores_Matches.csv` | includes `stage` |
| Brasileirão Série B / C | `BR-Football-Dataset.csv` | extended stats (shots, corners, attacks) |
| Players | `fifa_data.csv` | 18,207 FIFA player records |

---

## Testing

Behaviour-driven `clojure.test` scenarios (Given-When-Then) cover all five
capability areas plus the protocol:

- **normalize_test** — team-name canonicalization, club disambiguation, date &
  number parsing.
- **query_test** — match/team/player/competition/statistics queries, a
  regression guard that the 2019 Série A is a coherent 20-team/380-match table,
  and performance bounds (simple < 2s, aggregate < 5s).
- **mcp_test** — JSON-RPC handshake, `tools/list`, every tool via `tools/call`,
  error handling, and an end-to-end stdio round-trip.

```bash
clojure -M:test
# Ran 15 tests containing 120 assertions. 0 failures, 0 errors.
```

---

## Data Sources

Kaggle data can't be downloaded without an account, so these (freely available
with attribution) datasets were pre-downloaded into `data/kaggle/`:

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

See [brazilian-soccer-mcp-guide.md](brazilian-soccer-mcp-guide.md) (also
mirrored as `TASK.md`).
