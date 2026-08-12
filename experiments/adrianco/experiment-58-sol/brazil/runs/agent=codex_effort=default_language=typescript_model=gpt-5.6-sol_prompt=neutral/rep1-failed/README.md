# Brazilian Soccer MCP Server

A dependency-free, read-only Model Context Protocol server for the six bundled Brazilian soccer datasets. It normalizes their different schemas into one queryable match/player model and exposes typed MCP tools, a small relationship graph, resources, prompts, and deterministic natural-language routing.

## What it supports

- Search matches by team, opponent, home/away side, date range, competition, season, round, or stage.
- Calculate team records, goals, points, win rates, home/away performance, and head-to-head comparisons.
- Calculate standings from results and competition-wide goal/result statistics.
- Search 18,207 FIFA players by name, nationality, club, position family, rating, or age.
- Explore nodes and edges connecting teams, matches, competitions, and players.
- Route common natural-language questions such as “Who won the 2019 Brasileirão?” to the appropriate analysis.
- Read all five match files and the FIFA file, with source provenance retained when overlapping match rows are merged.

The server uses only local files and performs no network requests.

## Requirements and setup

- Node.js 20 or newer
- npm

```bash
npm install
npm test
npm start
```

`npm test` performs a strict TypeScript build, then runs 39 BDD-style tests, including an actual spawned stdio MCP exchange. Production has no runtime npm dependencies.

### Connect an MCP client

Build first with `npm run build`, then add a configuration like this to your MCP client (replace the path with this repository's absolute path):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "node",
      "args": ["/absolute/path/to/brazilian-soccer-mcp/dist/src/index.js"],
      "env": {
        "BRAZILIAN_SOCCER_DATA_DIR": "/absolute/path/to/brazilian-soccer-mcp/data/kaggle"
      }
    }
  }
}
```

The environment variable is optional when the process starts in the repository or uses the built entry point in place; it is useful for packaged or relocated deployments. The stdio transport reserves stdout for newline-delimited JSON-RPC responses and writes startup failures to stderr.

## MCP tools

| Tool | Purpose |
|---|---|
| `search_matches` | Filter and paginate normalized matches from all match sources |
| `get_team_statistics` | Compute a team record by season, competition, and venue |
| `compare_teams` | Return head-to-head matches and records |
| `search_players` | Filter and rank FIFA players |
| `get_standings` | Calculate a season table using three points per win |
| `get_competition_statistics` | Calculate goals, result rates, and biggest wins |
| `explore_soccer_graph` | Return a bounded team/player/match/competition node-edge graph |
| `answer_soccer_question` | Route a natural-language question to the relevant calculation |
| `dataset_summary` | Report coverage and per-file row counts |

All tools are marked read-only, non-destructive, idempotent, and closed-world. Results include both an MCP text content block and `structuredContent` for clients that can consume JSON directly.

The server also exposes:

- `soccer://dataset/summary` — loaded row and coverage metadata.
- `soccer://dataset/questions` — 20 representative supported questions.
- `analyze_brazilian_soccer` — a reusable prompt that instructs a model to stay grounded in the bundled data.

## Data model and quality handling

Five match schemas are converted into a single `SoccerMatch` shape. Dates in ISO, timestamp, and Brazilian `DD/MM/YYYY` formats become ISO dates. Team matching folds accents and punctuation, removes state suffixes, and resolves common full-name/abbreviation aliases such as `Atletico-MG`, `Athletico-PR`, and `Sport Club Corinthians Paulista`.

The match datasets overlap. Exact records and known one-day date shifts are merged only when competition, season, teams, and score also match; the merged row retains every contributing filename in `sources`. This prevents double-counted standings while keeping provenance auditable.

The graph is calculated from the normalized in-memory domain model rather than requiring a separate database. This keeps the demo portable while still returning explicit typed nodes and edges.

## Data limitations

- The FIFA file is a historical snapshot. A current Brazilian team may legitimately have no players in that file.
- Match files contain final scores, not goal-scorer events. The server explicitly reports that top scorers cannot be inferred rather than guessing.
- Standings and relegation answers are calculated only from matches present in the supplied files; they do not apply federation sanctions or competition-specific rule changes not encoded in the data.
- “Final” for numeric Copa do Brasil rounds is inferred as the highest round number in each season; Libertadores uses its stage labels.

## Project layout

```text
src/
  csv.ts              dependency-free UTF-8 CSV parser
  data-loader.ts      six-file adapters, merge, and provenance
  normalize.ts        names, dates, competitions, and aliases
  soccer-service.ts   query, analytics, graph, and NL routing
  mcp-server.ts       MCP JSON-RPC tools/resources/prompts over stdio
  index.ts            executable composition root
test/
  csv.test.ts
  service.test.ts
  mcp-server.test.ts
```

## Data attribution

- `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv` — Kaggle/ricardomattos05, CC BY 4.0.
- `BR-Football-Dataset.csv` — Kaggle/cuecacuela, CC0.
- `novo_campeonato_brasileiro.csv` — Kaggle/macedojleo, attribution license as supplied.
- `fifa_data.csv` — Kaggle/youssefelbadry10, Apache 2.0.

See [TASK.md](TASK.md) for the complete benchmark specification.
