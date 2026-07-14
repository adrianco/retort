# Brazilian Soccer MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) server, written in
TypeScript, that gives an LLM natural-language query access to Brazilian soccer
data: matches, teams, players and competitions. It implements the specification
in [`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md) (mirrored in
[`TASK.md`](TASK.md)).

## What it does

The server loads the six provided Kaggle CSV files (~24,000 matches and ~18,000
FIFA player records) into a unified in-memory model at startup, normalizes the
inconsistent team names / date formats / encodings, and exposes the spec's five
capability areas as MCP tools.

### Tools

| Tool | Capability area | Answers questions like |
|------|-----------------|------------------------|
| `search_matches` | Match queries | "Show me all Flamengo vs Fluminense matches", "What matches did Palmeiras play in 2023?", "Find Copa do Brasil matches in a date range" |
| `team_stats` | Team queries | "What is Corinthians' home record in 2022?" |
| `head_to_head` | Team queries | "Compare Palmeiras and Santos head-to-head" |
| `team_competitions` | Relationship queries | "What competitions has Palmeiras played in?" |
| `search_players` | Player queries | "Find all Brazilian players", "Who are the highest-rated players at Flamengo?", "Who is Gabriel Barbosa?" |
| `competition_standings` | Competition queries | "Who won the 2019 Brasileirão?" (table calculated from match results, 3-1-0) |
| `list_competitions` | Discovery | "What competitions and seasons are available?" |
| `match_statistics` | Statistical analysis | "Average goals per match?", "Biggest wins?", "Best home/away record?", "Most goals/wins in a season?" |

### Data handling

The loader (`src/dataLoader.ts`) and normalization helpers (`src/normalize.ts`)
address the data-quality notes from the spec:

- **Team name variations** — `"Palmeiras-SP"`, `"Palmeiras"`, `"Nacional (URU)"`
  all normalize to a common, accent-folded matching key, so queries match
  regardless of suffix or spelling.
- **Date formats** — ISO (`2023-09-24`), ISO with time (`2012-05-19 18:30:00`)
  and Brazilian (`29/03/2003`) are all parsed to ISO `YYYY-MM-DD`.
- **Character encoding** — UTF-8 throughout; accent-insensitive search means
  `"Sao Paulo"` matches `"São Paulo"` and `"Gremio"` matches `"Grêmio"`.
- **Competitions** — the differing source labels (`Serie A`, `tournament`
  column, etc.) are mapped to canonical names like `Brasileirão Série A`.

## Architecture

```
src/
  types.ts        Unified Match / Player / standings domain models
  normalize.ts    Team-name keys, accent folding, date & numeric parsing
  dataLoader.ts   Reads the 6 CSVs → unified model (cached, in-memory)
  queries.ts      Pure query/aggregation functions (the engine)
  format.ts       Renders results as human-readable text for the LLM
  server.ts       Registers MCP tools, wiring queries + formatters
  index.ts        Entry point — serves over stdio
tests/            BDD (Given/When/Then) scenarios, run with Vitest
```

The query engine is a set of **pure functions** with no I/O or MCP coupling,
which keeps it fast (every tool responds well under the spec's 2s/5s targets,
since all data is in memory) and trivially testable.

## Usage

### Install & build

```bash
npm install
npm run build
```

### Run

```bash
npm start          # runs the compiled server over stdio
# or, during development:
npm run dev
```

The data directory defaults to `./data/kaggle`. Override it with the
`BR_SOCCER_DATA_DIR` environment variable if needed.

### Connect from an MCP client

Example Claude Desktop config (`claude_desktop_config.json`):

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

## Testing

Tests follow the spec's **BDD / Given-When-Then** approach using Vitest. They
cover data loading & normalization, all five query capability areas, and a full
client→server round-trip over the MCP in-memory transport.

```bash
npm test
```

## Data Sources

Kaggle data can't be downloaded without an account, so these (freely available
with attribution) datasets have been downloaded for use here:

https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro
- License: Attribution 4.0 International (CC BY 4.0)
- `data/kaggle/Brasileirao_Matches.csv`
- `data/kaggle/Brazilian_Cup_Matches.csv`
- `data/kaggle/Libertadores_Matches.csv`

https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches
- License: CC0: Public Domain
- `data/kaggle/BR-Football-Dataset.csv`

https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019
- License: World Bank - Attribution 4.0 International (CC BY 4.0)
- `data/kaggle/novo_campeonato_brasileiro.csv`

https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data
- License: Apache 2.0
- `data/kaggle/fifa_data.csv`

## License

MIT (code). Datasets retain their original licenses as listed above. For
demo / non-commercial use.
