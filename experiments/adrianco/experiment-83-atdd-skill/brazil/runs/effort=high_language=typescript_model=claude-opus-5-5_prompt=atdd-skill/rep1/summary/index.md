# Architecture Summary — brazilian-soccer-mcp (typescript · opus-5-5 · atdd-skill)

## Modules

- **`src/index.ts`** — binary entrypoint; loads data from `data/kaggle/`, builds the knowledge base, wires it to the MCP server over stdio.
- **`src/server.ts`** — the MCP interface. Registers 18 tools (`search_matches`, `head_to_head`, `team_record`, `team_competitions`, `team_rankings`, `team_profile`, `standings`, `cup_finals`, `knockout_bracket`, `find_derbies`, `competition_stats`, `biggest_wins`, `compare_seasons`, `search_players`, `get_player`, `brazilian_club_squads`, `dataset_info`) with zod input schemas; each delegates to `SoccerKnowledge` and wraps results/`QueryError` into `CallToolResult`.
- **`src/domain/`** — the football model, framework-free:
  - `model.ts` — `Match`, `Player`, `MatchStats`, `Competition` types.
  - `teams.ts` — `TeamRegistry` + `parseTeamName`: normalises name variants ("Palmeiras-SP" / "Palmeiras" / full names), state suffixes, accents.
  - `knowledge.ts` (~700 lines) — `SoccerKnowledge`: all query/aggregation logic (match search, records, head-to-head, standings computed from results, knockout brackets, derbies, stats, player search).
  - `records.ts`, `derbies.ts` — W/L/D aggregation and rivalry definitions.
- **`src/data/`** — ingestion:
  - `csv.ts` — BOM-aware, quote-aware CSV reader.
  - `dates.ts` — multi-format date parsing (ISO, Brazilian DD/MM/YYYY, with time).
  - `loader.ts` — reads all six CSVs, dedupes matches appearing in multiple datasets, links FIFA players to clubs.
- **`src/text.ts`** — response formatting helpers.

## Test architecture (ATDD four-layer)

- **Test cases** (`tests/acceptance/*.spec.ts`, 49 specs) — written purely in football language via a `spec()` DSL; most build synthetic data (isolated), `provided-datasets.spec.ts` runs against real Kaggle data and asserts real facts (2019 Flamengo champion 90 pts; 2020 Copa do Brasil final; top Brazilian player).
- **DSL** (`tests/acceptance/dsl/`) — `given`, `matches`, `players`, `teams`, `competitions`, `statistics`, `datasets` — the problem-domain vocabulary.
- **Drivers** (`tests/acceptance/drivers/`) — `mcp-soccer-driver.ts` drives the system end-to-end as a real MCP stdio client against the built server; `dataset-writer.ts` seeds synthetic CSVs.
- **Unit** (`tests/unit/parsing.test.ts`, 4 tests) — team-name/date/CSV parsing edge cases.

## Flow

LLM → MCP tool call → `server.ts` tool handler → `SoccerKnowledge` method → normalised `Match`/`Player` data (loaded once at startup) → `Answer{text,data}` → `CallToolResult`.

## Notes

- Dependencies are minimal and appropriate: `@modelcontextprotocol/sdk`, `zod` (runtime); `typescript`, `vitest`, `@types/node` (dev).
- Standings, head-to-head and all statistics are **computed from match results**, not hardcoded.
