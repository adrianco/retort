# Brazilian Soccer MCP Server

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server that turns the
bundled Kaggle datasets into a queryable knowledge base of Brazilian soccer — matches,
teams, competitions and FIFA player data — so an LLM client can answer natural-language
questions like *"What is Corinthians' home record in 2022?"* or *"Who won the 2019
Brasileirão?"*.

It is written in TypeScript and built test-first (executable ATDD): every requirement in
[`TASK.md`](TASK.md) is pinned by an acceptance test that drives the system **only through
the MCP protocol**, with finer-grained unit tests underneath.

---

## Quick start

```bash
npm install
npm test          # run the full acceptance + unit suite
npm run build     # compile TypeScript to dist/
npm start         # run the MCP server over stdio
```

The server loads `data/kaggle/*.csv` on startup (~21k matches, ~18k players) and serves
over **stdio**. Point any MCP-capable client at it, e.g. a `claude_desktop_config.json`
entry:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "node",
      "args": ["/absolute/path/to/dist/src/index.js"]
    }
  }
}
```

The data directory is resolved from `$BRAZILIAN_SOCCER_DATA_DIR`, then `./data/kaggle`,
then relative to the compiled file.

---

## MCP tools

Every tool returns a structured JSON payload (also surfaced as `structuredContent`) plus a
human-readable `summary` string.

| Tool | Answers questions like | Key parameters |
|------|------------------------|----------------|
| `find_matches` | "Show me all Flamengo vs Fluminense matches"; "What matches did Palmeiras play in 2023?"; "Find Libertadores finals" | `team`, `opponent`, `homeTeam`, `awayTeam`, `competition`, `stage`, `season`, `dateFrom`, `dateTo`, `limit` |
| `head_to_head` | "Compare Palmeiras and Santos head-to-head" | `team1`, `team2`, `competition?`, `season?` |
| `team_record` | "What is Corinthians' home record in 2022?" | `team`, `season?`, `competition?`, `venue?` (home/away/all) |
| `find_players` | "Find all Brazilian players"; "Highest-rated players at a club"; "Forwards from a club" | `name`, `nationality`, `club`, `position`, `minOverall`, `sortBy`, `limit` |
| `competition_standings` | "Who won the 2019 Brasileirão?" (table calculated from results) | `competition`, `season` |
| `competition_statistics` | "Average goals per match"; "Biggest wins"; "Home win rate" | `competition?`, `season?` |
| `dataset_summary` | "What data is loaded?" | — |

Standings are computed from match results (3 pts win / 1 pt draw), ranked by points, then
goal difference, then goals for.

---

## How the messy data is handled

The datasets use inconsistent conventions (see `TASK.md` → *Data Quality Notes*). All
normalization lives in the `DataStore`, which owns a single source of truth:

- **Team name variations.** `"Palmeiras-SP"`, `"Palmeiras"`, `"América - MG"` and
  `"Nacional (URU)"` are reconciled to a canonical key (accent-, case- and
  suffix-insensitive), so a query for `"Palmeiras"` finds `"Palmeiras-SP"`.
- **Same-name clubs in different states.** Naively stripping the state suffix would merge
  genuinely different clubs that share a base name (e.g. **Atlético-MG** vs **Atlético-PR**,
  the latter spelled both `Athletico-PR` and `Atletico-PR` across files). The store does a
  two-pass index build: it detects base names that occur with *multiple* states and keeps
  the state as part of those clubs' identity, while still unifying unambiguous cases like
  `Flamengo-RJ`/`Flamengo`. Authoritative state columns (`home_team_state`, `Mandante_UF`)
  are used when present, so suffix-less names are still tied to their state.
- **Duplicate fixtures.** The same physical match recorded in two source files (e.g. the
  2003–2019 historical file overlaps the main Brasileirão file) is de-duplicated by
  `(competition, season, date, teams, score)` — so a 38-game season reports 38 games, not 76.
- **Date formats.** ISO, ISO-with-time and Brazilian `DD/MM/YYYY` are all parsed to ISO.
- **UTF-8.** Accents and cedillas (`São`, `Grêmio`, `Avaí`) are preserved in display names
  and folded for matching.

This is validated end-to-end: the real-data acceptance test reconstructs the **2019
Brasileirão** as a 20-team table with **Flamengo champion on 90 points** — the correct
historical result.

---

## Provided data

| File | Rows | Competition(s) | License |
|------|------|----------------|---------|
| `Brasileirao_Matches.csv` | 4,180 | Brasileirão Série A | CC BY 4.0 |
| `Brazilian_Cup_Matches.csv` | 1,337 | Copa do Brasil | CC BY 4.0 |
| `Libertadores_Matches.csv` | 1,255 | Copa Libertadores | CC BY 4.0 |
| `BR-Football-Dataset.csv` | 10,296 | Série A/B/C, Copa do Brasil (extended stats) | CC0 |
| `novo_campeonato_brasileiro.csv` | 6,886 | Brasileirão 2003–2019 | CC BY 4.0 |
| `fifa_data.csv` | 18,207 | FIFA player database | Apache 2.0 |

Sources:
- https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro
- https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches
- https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019
- https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data

Full specification: [`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md) (identical to `TASK.md`).

---

## Architecture

```
src/
  domain/
    types.ts        Match, Player domain types
    normalize.ts    team-name / date / state / word-match normalization
  data/
    store.ts        DataStore — seeding, two-pass index, all query logic
    loaders.ts      CSV → canonical records, one loader per file
  server.ts         createSoccerServer(store) — registers the MCP tools (thin adapter)
  index.ts          stdio entry point: load data, serve
tests/
  acceptance/       black-box tests driven through the MCP client (in-memory transport)
  unit/             normalization + loader unit tests
```

The MCP layer is a thin adapter; querying and aggregation live in `DataStore`, keeping the
tools easy to test and reason about.

### Testing approach (ATDD)

Acceptance tests connect a real MCP `Client` to the real server over an in-memory transport
pair, so they exercise the public protocol with no back-door access to internals. Each test
starts from a fresh, empty system and seeds its own data, making scenarios atomic and
independent. A separate suite runs the production CSV-loading path against the shipped
datasets and queries them through the same MCP interface.

```bash
npm test            # 52 tests: acceptance (protocol + real data) and unit
npm run typecheck   # tsc --noEmit
```

---

## Known limitations

- Copa do Brasil match rows label rounds numerically (1–8) rather than `"final"`, so
  stage-name searches don't surface its finals; the Libertadores file does carry named
  stages (`group stage`, `final`, …).
- The extended `BR-Football-Dataset.csv` labels the top flight `"Serie A"`, which is kept
  distinct from `"Brasileirão"`; filter by the competition you want.
- Disambiguating two clubs that share a base name *and* a state, or unifying entirely
  different name forms, would require a curated club registry, which is out of scope for
  this demo.

## License

Demo / non-commercial use. Dataset licenses are listed above and retained with their files.
