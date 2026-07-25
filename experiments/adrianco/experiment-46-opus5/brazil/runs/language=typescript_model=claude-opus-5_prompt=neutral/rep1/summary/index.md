# Architecture Summary — Brazilian Soccer MCP Server (TypeScript)

MCP server exposing a knowledge graph over Brazilian soccer datasets. Layered
ESM/TypeScript codebase (4,634 LOC across 27 source files), strict separation of
data loading → domain model → query engine → tool adapters → MCP transport.

## Layers

- **`src/index.ts` / `src/server.ts`** — MCP entrypoint. `createServer(graph)`
  wires the transport-agnostic tool catalogue onto `McpServer` from
  `@modelcontextprotocol/sdk`, registering each tool with a Zod input schema and
  `readOnlyHint` annotations. Handler errors are returned as `isError` results
  (with candidate suggestions) rather than thrown.

- **`src/data/`** — CSV ingestion. `loadMatches.ts` reads the five match CSVs
  into `RawMatch` records then **de-duplicates by fixture** (`mergeMatches`,
  source-confidence ranking) so overlapping Série A seasons are not
  triple-counted — critical for correct aggregates. `loadPlayers.ts` loads the
  18k-row FIFA database. `paths.ts` enumerates `data/kaggle/` files.

- **`src/domain/`** — `teams.ts` (571 LOC) is a team-name normalization
  registry handling state suffixes, accents, and full-name variants (spec's
  "Data Quality Notes"). `dates.ts` parses ISO + Brazilian date formats.
  `types.ts` defines `Match`, `Player`, `CompetitionId`, outcome helpers.

- **`src/graph/graph.ts`** — `SoccerGraph`: builds team/competition/season
  indexes over the merged fixtures + players so queries start from the narrowest
  index rather than scanning all ~16.8k matches.

- **`src/query/`** — pure query engine. `filters.ts` (`selectMatches` with
  home/away/either venue, competition, season range, date range, stage, margin).
  `teamQueries.ts` (records, head-to-head, profiles → `TeamRecord`).
  `competitionQueries.ts` (standings replayed from results, inferred champion +
  relegation with `complete` flag). `playerQueries.ts` (layered name matching:
  exact → prefix/substring → fuzzy; nationality/club/position/rating filters).
  `statsQueries.ts` (goals/match, home vs away, extremes, season comparison).

- **`src/tools/`** — 17 tool definitions adapting query functions to MCP tools
  (`search_matches`, `head_to_head`, `find_derbies`, `team_stats`,
  `team_profile`, `team_rankings`, `search_players`, `player_profile`,
  `club_squad`, `competition_standings`, `competition_bracket`,
  `match_statistics`, `record_extremes`, `compare_seasons`, `dataset_info`,
  `list_seasons`, `list_teams`). Each returns both prose text and
  `structuredContent`.

- **`src/format/format.ts`**, **`src/cli/ask.ts`** — human-readable formatting
  and a `tsx` CLI (`npm run ask`) for manual querying.

## Tests (`tests/`, 1,963 LOC, 122 cases)

- `mcp.test.ts` — end-to-end via a real SDK `Client` over `InMemoryTransport`
  (manifest, JSON-Schema generation, argument validation, error results).
- `unit/` — teams, dates, csv, graph, merge/de-dup, tools.
- `bdd.test.ts` + `tests/features/*.feature` — Gherkin BDD scenarios (match,
  team, player, competition, statistics) matching the spec's testing approach.
- `sampleQuestions.test.ts` — spec's ≥20 sample questions.
- `performance.test.ts` — latency budgets (<2s lookups, <5s aggregates).

## Flow

`index.ts` → load & merge CSVs → build `SoccerGraph` → `createServer` registers
tools → MCP client calls tool → Zod-validated args → query engine reads graph
indexes → result formatted as text + structured data.
