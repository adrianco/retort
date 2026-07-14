# Brazilian Soccer MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) (MCP) server, written
in TypeScript, that exposes a knowledge interface over Brazilian soccer data:
matches, teams, players and competitions. Connect it to an MCP-capable LLM
client (Claude Desktop, Claude Code, etc.) and ask natural-language questions —
the model picks the right tool and the server answers from the bundled datasets.

Implemented against the specification in
[`brazilian-soccer-mcp-guide.md`](./brazilian-soccer-mcp-guide.md) /
[`TASK.md`](./TASK.md).

---

## What was built

- **Unified data layer** — all six Kaggle CSVs (≈24k raw match rows + 18,207 FIFA
  players) are loaded into a single in-memory model. The loader handles UTF-8
  accents, three date formats (ISO, ISO+time, Brazilian `DD/MM/YYYY`), and
  defensive numeric parsing (blank / `NA` / float cells → `number | null`).
- **Team-name normalisation** — collapses naming variants (`Palmeiras-SP` ≡
  `Palmeiras`, `São Paulo` ≡ `Sao Paulo`, `Vasco` ≡ `Vasco da Gama`) while keeping
  genuinely different clubs apart (`Atlético-MG` ≠ `Athletico-PR`).
- **Cross-file de-duplication** — the same fixture appears in up to three files
  (e.g. 2012–2019 Brasileirão is double-listed, and re-listed again as "Serie A"
  in the extended-stats file). Duplicates are collapsed by `date + teams` so
  reconstructed standings aren't inflated 2–3×; extended match stats are grafted
  onto the canonical row, and the extended file's Série B / C coverage is kept.
- **Five query services** — matches, teams, players, competitions and statistics
  (see below), each a pure module with a structured return type.
- **MCP server** — 10 tools over stdio, validated with `zod`, returning
  human-readable formatted text.
- **BDD test suite** — 45 Given-When-Then specs (Vitest), including an
  end-to-end test that drives the server through a real in-memory MCP client.

Every source file opens with a `CONTEXT` block comment describing its role.

---

## Capabilities & tools

| Capability (spec) | MCP tool(s) | Example question |
|---|---|---|
| Match Queries | `search_matches`, `head_to_head` | "Show me all Flamengo vs Fluminense matches" |
| Team Queries | `team_record` | "What is Corinthians' home record in 2022?" |
| Player Queries | `search_players`, `club_player_breakdown` | "Who are the top Brazilian players?" |
| Competition Queries | `standings`, `list_seasons` | "Who won the 2019 Brasileirão?" |
| Statistical Analysis | `match_statistics`, `biggest_wins`, `team_rankings` | "Which team has the best home record?" |

Reconstructed 2019 Brasileirão (from match results) — matches the spec's ground truth:

```
2019 Brasileirão Standings (calculated from matches):
1. Flamengo - 90 pts (28W 6D 4L, GF 86 GA 37) - Champion
2. Palmeiras - 74 pts (21W 11D 6L, GF 61 GA 32)
3. Santos - 74 pts (22W 8D 8L, GF 60 GA 33)
...
```

---

## Datasets

| File | Rows | Content |
|---|---|---|
| `Brasileirao_Matches.csv` | 4,180 | Brasileirão Série A (2012–2022) |
| `novo_campeonato_brasileiro.csv` | 6,886 | Historical Brasileirão (2003–2019) |
| `Brazilian_Cup_Matches.csv` | 1,337 | Copa do Brasil |
| `Libertadores_Matches.csv` | 1,255 | Copa Libertadores |
| `BR-Football-Dataset.csv` | 10,296 | Extended stats; Série A/B/C + Copa do Brasil |
| `fifa_data.csv` | 18,207 | FIFA player ratings & attributes |

Sources and licenses:

- https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro — CC BY 4.0
  (`Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`)
- https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches — CC0 Public Domain
  (`BR-Football-Dataset.csv`)
- https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019 — CC BY 4.0
  (`novo_campeonato_brasileiro.csv`)
- https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data — Apache 2.0
  (`fifa_data.csv`)

---

## Getting started

Requires Node.js ≥ 18.

```bash
npm install
npm run build      # compile TypeScript to dist/
npm test           # run the BDD test suite (45 specs)
npm start          # run the MCP server over stdio
```

During development you can run the server without building via `npm run dev`.

### Connecting an MCP client

Add the server to your client's MCP config (example for Claude Desktop):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "node",
      "args": ["/absolute/path/to/dist/index.js"]
    }
  }
}
```

The server logs to **stderr** only; **stdout** carries the MCP JSON-RPC stream.

---

## Tool reference

- **`search_matches`** `{ team?, opponent?, competition?, season?, dateFrom?, dateTo?, venue?, limit? }`
  — matches by any combination of criteria, most-recent first.
- **`head_to_head`** `{ teamA, teamB, competition?, season? }` — rivalry tally + match list.
- **`team_record`** `{ team, season?, competition?, venue? }` — W/D/L, goals, points, win rate.
- **`search_players`** `{ name?, nationality?, club?, position?, minOverall?, sortBy?, limit? }`
  — FIFA player search.
- **`club_player_breakdown`** `{ nationality?, position?, minOverall?, topN? }`
  — players grouped by club with count + average rating.
- **`standings`** `{ competition, season, relegationCount? }` — reconstructed league table.
- **`list_seasons`** `{ competition? }` — seasons available in the data.
- **`match_statistics`** `{ competition?, season?, team? }` — avg goals, home/draw/away rates.
- **`biggest_wins`** `{ competition?, season?, team?, limit? }` — largest winning margins.
- **`team_rankings`** `{ competition?, season?, venue?, metric?, minMatches?, limit? }`
  — rank teams by record (best home/away record, most points, etc.).

---

## Architecture

```
src/
  types.ts              Unified Match / Player / Dataset domain types
  data/
    normalize.ts        Team-name normalisation & matching
    loader.ts           CSV parsing, date/number handling, de-duplication
  services/
    matches.ts          findMatches + head-to-head (foundational filter layer)
    teams.ts            Team records
    players.ts          Player search + club breakdown
    competitions.ts     Standings, champions, relegation
    stats.ts            Aggregates, biggest wins, team rankings
  format.ts             Structured results -> human-readable text
  server.ts             MCP tool definitions
  index.ts              stdio entry point
tests/                  Vitest BDD (Given-When-Then) specs
```

Design notes:

- Services return **structured data**; presentation lives in `format.ts`, so the
  same logic is unit-tested structurally and surfaced as text via the tools.
- All team comparison funnels through one primitive (`teamMatches`) so naming
  variants resolve consistently everywhere.
- The dataset loads once and is cached, keeping simple lookups < 2 s and
  aggregate queries < 5 s (per the spec's performance targets).

---

## Data-quality handling

- **Team names** — state suffixes, country codes, accents and full-vs-short names
  are normalised; state-ambiguous bases (Atlético, América, Nacional) keep their
  state code so distinct clubs stay distinct.
- **Dates** — ISO, ISO+time and Brazilian `DD/MM/YYYY` all normalise to ISO.
- **Encoding** — files are read as UTF-8 (the FIFA file's BOM is stripped).
- **Missing scores** — some late-season rows (e.g. the last 4 Corinthians 2022
  home games) were unplayed when the dataset was captured; these are reported as
  fixtures but excluded from win/draw/loss tallies.
- **Note** — the FIFA player set predates Brazilian-league club licensing for some
  clubs, so a few clubs (e.g. Flamengo) have no FIFA squad entries; many others
  (Grêmio, Santos, Internacional, …) are present.
