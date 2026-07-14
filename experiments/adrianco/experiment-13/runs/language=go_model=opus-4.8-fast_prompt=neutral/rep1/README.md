# Brazilian Soccer MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) server, written in Go,
that exposes a knowledge graph over Brazilian-soccer datasets (Brasileirão,
Copa do Brasil and Copa Libertadores match results, plus the FIFA player
database). An LLM client connects over stdio and calls the server's tools to
answer natural-language questions about matches, teams, players, competitions
and statistics.

It implements the specification in [`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md)
(mirrored in `TASK.md`).

## Quick start

```bash
go build -o bsmcp .          # build
./bsmcp                       # serve MCP over stdio (reads ./data/kaggle)
./bsmcp -data path/to/csvs    # point at a different data directory
./bsmcp -demo                 # print answers to ~13 sample questions and exit
go test ./...                 # run the test suite
```

Diagnostics (rows loaded per file, duplicates dropped) go to **stderr**, so the
stdio JSON-RPC stream on **stdout** stays clean.

### Using it from an MCP client

The server speaks JSON-RPC 2.0 over newline-delimited stdio. A typical client
config:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/bsmcp",
      "args": ["-data", "/absolute/path/to/data/kaggle"]
    }
  }
}
```

You can also drive it by hand:

```bash
printf '%s\n' \
 '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
 '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
 '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"standings","arguments":{"competition":"Brasileirão","season":2019,"limit":5}}}' \
 | ./bsmcp
```

## Tools

The server registers 12 tools spanning the five capability areas in the spec:

| Tool | What it answers |
|------|-----------------|
| `search_matches` | Matches by team / opponent / competition / season / date range (+ H2H summary when two teams are given) |
| `head_to_head` | Two teams compared: matches, W/D/L, goals, recent meetings |
| `team_record` | A team's W/D/L, goals and points, optionally by competition / season / home-away |
| `team_competitions` | Which competitions a team appears in, with counts and season ranges |
| `standings` | League table for a competition + season, computed from results |
| `competition_stats` | Matches, total goals, avg goals/match, home/away/draw rates |
| `biggest_wins` | Largest-margin victories |
| `top_scoring_teams` | Teams ranked by goals scored |
| `search_players` | FIFA players by name / nationality / club / position / rating |
| `player_info` | Detailed card for one player |
| `club_players` | A club's squad (top-rated first) with average rating |
| `dataset_overview` | What's loaded: counts and per-competition season ranges |

Example (`-demo` output):

```
2019 Brasileirão Série A standings (calculated from 380 matches):
 1. Flamengo-RJ - 90 pts (28W, 6D, 4L), GF 86 GA 37 (+49)
 2. Santos-SP   - 74 pts (22W, 8D, 8L), GF 60 GA 33 (+27)
 3. Palmeiras   - 74 pts (21W, 11D, 6L), GF 61 GA 32 (+29)
...
Champion: Flamengo-RJ (90 pts).
```

(This matches the worked example in the spec.)

## Design notes

The interesting work is in the data layer, not the protocol.

- **One unified model.** The five match datasets have different columns, date
  formats and naming conventions; per-file loaders normalize them all into a
  single `Match` shape and map competition labels onto canonical names
  (`Serie A` → *Brasileirão Série A*, etc.).

- **Ambiguity-aware team names.** The same club is written many ways
  (`Palmeiras-SP`, `Palmeiras`, `São Paulo` vs `Sao Paulo`). Naively stripping
  the state suffix is wrong, because the suffix is sometimes the *only*
  disambiguator — `Atlético-MG` (Mineiro) vs `Athletico-PR` (Paranaense), or
  `Flamengo-RJ` vs `Flamengo-PI`. So the matcher first scans every name to learn
  which base names are shared across states, then keeps the state **only** for
  those. Spelling quirks are handled too (`Athletico` → Paranaense; the
  spelled-out `Atletico Mineiro`/`Paranaense`/`Goianiense` forms used by one
  dataset alias onto the suffixed identity). Ambiguous user queries (just
  "Atletico") return a disambiguation prompt instead of wrong data.

- **Accents and dates.** UTF-8 accents are folded for matching (`Grêmio` →
  `gremio`) while display keeps the original spelling. Multiple date formats are
  parsed (`2012-05-19 18:30:00`, `29/03/2003`, `2023-09-24`).

- **Cross-source de-duplication.** The Brasileirão appears in three sources with
  overlapping years. Identical fixtures (same competition, day, teams, score)
  are de-duplicated. Because a late kickoff can cross midnight, some sources
  disagree on the calendar day, so for **season-level aggregates** (standings,
  per-season stats and rankings) the server instead uses the single most
  complete source per (competition, season) — which is what makes the 2019
  table come out to exactly 380 matches.

## Architecture

```
main.go              entry point, flags, -demo mode
tools.go             registers the 12 MCP tools (JSON-Schema + handlers)
mcp/                 dependency-free MCP server over stdio (JSON-RPC 2.0)
soccer/
  normalize.go       team-name / accent normalization
  models.go          Match and Player models, canonical competition names
  loader.go          per-file CSV ingestion
  store.go           in-memory graph: keys, de-dup, fuzzy resolution, queries
  stats.go           pure aggregate analysis (records, standings, H2H, ...)
  format.go          human-readable rendering
  queries.go         high-level query API the tools call
```

No third-party dependencies — only the Go standard library.

## Tests

`go test ./...` covers normalization (incl. the Atlético/Athletico edge case),
loading, de-duplication, the analysis functions, the high-level queries against
the real datasets (e.g. the 2019 champion), and the MCP protocol layer
(handshake, `tools/list`, `tools/call`, error handling) end-to-end. Tests that
need the CSVs skip cleanly if the data directory is absent.

## Data Sources

Kaggle data can't be downloaded without an account, so these (freely available
with attribution) datasets are bundled under `data/kaggle/`:

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
