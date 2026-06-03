# Brazilian Soccer MCP Server

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server that
turns the bundled Brazilian-soccer Kaggle datasets into a queryable knowledge
interface. An LLM client (e.g. Claude Desktop) can ask natural-language
questions about matches, teams, players, competitions and statistics; the
server answers from the CSV data with both a human-readable text block and a
structured JSON payload.

Implemented in **TypeScript** on the official `@modelcontextprotocol/sdk`, with
a **BDD (Given/When/Then)** test suite run by Vitest.

## What was built

| Layer | File | Responsibility |
|-------|------|----------------|
| Types | `src/types.ts` | Unified `Match` / `Player` / `Record` shapes |
| Normalization | `src/normalize.ts` | Team-name & date normalization, accent-insensitive matching |
| Data store | `src/dataStore.ts` | Loads & **de-duplicates** all 6 CSVs into memory |
| Queries | `src/queries.ts` | Pure query functions (matches, teams, players, standings, stats) |
| Formatting | `src/format.ts` | Renders results into the spec's text answer format |
| MCP server | `src/server.ts` | Registers the tools, validates input with zod |
| Entry point | `src/index.ts` | Loads data and serves over stdio |

Every source file opens with a `Context` comment block describing its role.

## Data handled

All six provided files in `data/kaggle/` are loaded and queryable:

- `Brasileirao_Matches.csv` — Brasileirão Série A
- `Brazilian_Cup_Matches.csv` — Copa do Brasil
- `Libertadores_Matches.csv` — Copa Libertadores
- `BR-Football-Dataset.csv` — Série A/B/C + Copa do Brasil (extended stats)
- `novo_campeonato_brasileiro.csv` — historical Brasileirão 2003–2019
- `fifa_data.csv` — 18,207 FIFA players

The files overlap heavily (Série A 2012–2019 appears in three of them), so
matches are **de-duplicated** on `(competition, season, home, away)`, keeping
the most detailed record. This is what makes computed standings correct — e.g.
the 2019 Brasileirão table returns exactly 20 teams with Flamengo champions on
90 points, matching the official result.

### Data-quality handling

- **Team-name variations** — `Palmeiras-SP`, `América - MG`, `Nacional (URU)`,
  `Botafogo RJ`, `São Paulo FC`, `EC Bahia` are all normalized; matching is
  accent-insensitive (`Grêmio` ≈ `gremio`), and `Athletico`-PR vs `Atlético`-MG
  are kept distinct via an alias table.
- **Date formats** — ISO (`2023-09-24`), datetime (`2012-05-19 18:30:00`) and
  Brazilian (`29/03/2003`) all normalize to ISO `YYYY-MM-DD`.
- **Encoding** — files are read as UTF-8; the BOM on `fifa_data.csv` is stripped.

## Tools exposed

| Tool | Purpose |
|------|---------|
| `search_matches` | Matches by team / opponent / competition / season / date range |
| `head_to_head` | Win-draw-loss record between two teams |
| `team_stats` | A team's record, goals and home/away split (scoped by comp/season) |
| `team_competitions` | Which competitions a team appears in |
| `search_players` | FIFA players by name / nationality / club / position / rating |
| `get_player` | Full attributes for the best-matching player |
| `competition_standings` | League table computed from results (3pt win / 1pt draw) |
| `competition_stats` | Avg goals, total goals, home/away/draw split, home win rate |
| `biggest_wins` | Largest goal-margin victories |
| `top_scoring_teams` | Teams ranked by goals scored |

## Setup

```bash
npm install
npm run build
```

## Run

```bash
npm start            # node dist/index.js  (serves over stdio)
# or, without building:
npm run dev          # tsx src/index.ts
```

The data directory defaults to `./data/kaggle`; override with the
`SOCCER_DATA_DIR` environment variable.

### Use with Claude Desktop

Add to `claude_desktop_config.json`:

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

## Test (BDD)

```bash
npm test
```

40 Given/When/Then scenarios across seven feature files cover normalization,
match queries, team queries, player queries, competition standings, statistical
analysis, and an end-to-end MCP client↔server integration test. All pass.

## Known data limitations

- The bundled FIFA export (FIFA 19) includes many Brazilian clubs (Santos,
  Grêmio, Internacional, Fluminense, …) and 800+ Brazilian players, but omits a
  few big clubs such as Flamengo and Palmeiras for licensing reasons. Queries
  for those clubs honestly return no players rather than fabricating data.
- Seasons after ~2021 are only partially present (they come solely from
  `BR-Football-Dataset.csv`), so recent standings may be incomplete.
- Distinct clubs that share a short name and state-stripping (e.g. América-MG
  vs América-RN) can collapse together; the common Série A clubs are unaffected.

## Data sources & licenses

See the source list below — all datasets are freely available with attribution.

- Jogos do Campeonato Brasileiro — CC BY 4.0 — https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro
- Brazilian Football Matches — CC0 — https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches
- Campeonato Brasileiro 2003–2019 — CC BY 4.0 — https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019
- FIFA Players Data — Apache 2.0 — https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data
