# Brazilian Soccer MCP Server

A read-only Model Context Protocol server for the six CSV datasets bundled in this repository. It loads and normalizes Brazilian match and FIFA player data, exposes focused query tools, and can route common natural-language soccer questions without a database or external API.

## Capabilities

- Search matches by team, opponent, home/away side, date, season, competition, round, or stage.
- Calculate team records, head-to-head results, standings, goal averages, outcome rates, and biggest victories.
- Search FIFA players by name, nationality, club, position, overall rating, or potential.
- Return graph-shaped team relationships to competitions, opponents, and players.
- Answer common English natural-language questions through `answer_question`.
- Normalize accents, state suffixes, full club names, aliases, ISO dates, timestamps, and Brazilian dates.
- Retain file-and-row provenance and avoid double-counting overlapping competition data in analytics.

This is historical, bundled data—not a live scores service. Player-level goal events are absent, so top scorers cannot be inferred reliably. Calculated standings reflect the completed records present in each source; some recent seasons are incomplete.

## Install and run

Requires Node.js 20 or newer.

```bash
npm install
npm run build
npm test
npm start
```

The server uses stdio. Do not write application logs to stdout because stdout carries MCP protocol messages.

To use another compatible set of six files, set `SOCCER_DATA_DIR`:

```bash
SOCCER_DATA_DIR=/absolute/path/to/csvs npm start
```

### MCP client configuration

After building, add this shape to an MCP-capable client's configuration, replacing the path with this repository's absolute path:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "node",
      "args": ["/absolute/path/to/brazilian-soccer-mcp/dist/index.js"]
    }
  }
}
```

For development, the command can instead be `npx` with arguments `tsx` and `/absolute/path/to/src/index.ts`.

## MCP tools

| Tool | Purpose |
|---|---|
| `dataset_summary` | Loaded sources, row counts, competitions, and date coverage |
| `search_matches` | Paginated match search across every provided match source |
| `team_statistics` | Wins/draws/losses, goals, points, and home/away records |
| `head_to_head` | Meetings and aggregate results for two teams |
| `search_players` | Ranked FIFA player search |
| `calculate_standings` | Season standings from match results |
| `competition_summary` | Teams, stages/rounds, date span, and calculated leader |
| `analyze_statistics` | Goals per match, outcome rates, and biggest wins |
| `explore_relationships` | Nodes and edges around a team |
| `answer_question` | Natural-language routing over the operations above |

Every tool returns both readable text and `structuredContent` suitable for programmatic clients.

## Example questions

- “Show me all Flamengo vs Fluminense matches.”
- “What matches did Palmeiras play in 2023?”
- “What is Corinthians' home record in 2022?”
- “Who won the 2019 Brasileirão?”
- “Who are the highest-rated Brazilian players?”
- “What's the average goals per match in the Brasileirão?”
- “Which team has the best away record?”
- “Show all derbies in 2019.”

For less common requests, MCP clients should call the focused tools directly; their schemas support combinations beyond the lightweight natural-language router.

## Development

```bash
npm run check          # compile and run all tests
npm run dev            # run the TypeScript stdio server
npm run test:coverage  # requires @vitest/coverage-v8 if not already installed
```

The implementation is split into source adapters and canonical data loading (`src/data-store.ts`), normalization (`src/normalize.ts`), domain queries (`src/service.ts`), natural-language routing (`src/query.ts`), formatting, and MCP registration. Tests use small deterministic fixtures plus the real bundled data and include a protocol-level in-memory client/server call.

## Data attribution

- `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, and `Libertadores_Matches.csv`: Ricardo Mattos, CC BY 4.0.
- `BR-Football-Dataset.csv`: cuecacuela, CC0 Public Domain.
- `novo_campeonato_brasileiro.csv`: macedojleo, attribution license as documented by the source dataset.
- `fifa_data.csv`: Youssef Elbadry, Apache 2.0.

See [TASK.md](TASK.md) for the full supplied specification and original dataset links.
