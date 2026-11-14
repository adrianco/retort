# Architecture summary — brazilian-soccer-mcp (TypeScript)

An MCP (Model Context Protocol) stdio server that answers natural-language-style
queries about Brazilian soccer from six Kaggle CSV files. Layered: CSV → model →
query engine → MCP tools.

## Modules

| File | LOC | Responsibility |
|------|-----|----------------|
| `src/index.ts` | 19 | Entry point. `loadDataset()` → `SoccerDB` → `createServer()` → `StdioServerTransport`; logs readiness to stderr (stdout reserved for the protocol). |
| `src/csv.ts` | 41 | Minimal RFC-4180 CSV parser: quoted fields, escaped quotes, embedded commas, CRLF, UTF-8 BOM. Returns `Record<string,string>[]`. |
| `src/normalize.ts` | 229 | Shared normalisation. `clean()` folds accents/punctuation; `teamKey()` maps club-name variants ("Palmeiras-SP", "Sport Club Corinthians Paulista") to one key via an alias table + ambiguous-base handling; `parseDate()` (ISO / ISO+time / DD/MM/YYYY), `parseNum()`, `parseCompetition()`; `Competition` union + `COMPETITIONS`. |
| `src/data.ts` | 299 | `loadDataset()` reads all six CSVs into a unified `Match[]` + `Player[]` model. `markPrimary()` de-duplicates overlapping Série A/Copa seasons across files (one preferred source per competition/season); `markCupFinals()` labels the last cup round "final". Data dir overridable via `BRAZILIAN_SOCCER_DATA_DIR`. |
| `src/queries.ts` | 655 | `SoccerDB` query engine: `findMatches` (team/venue/competition/season/date/stage/round, dedup-aware), `tally`, `headToHead`, `teamStats`, `teamProfile`, `standings` (3pts/win, champion + relegation, completeness check), `cupSummary` (stage grouping + two-leg ties/aggregates), `leagueStats`, `biggestWins`, `rankTeams`, `compareSeasons`, `derbies` (rivalry table), `extendedStats` (corners/shots/attacks), `searchPlayers` (name/nationality/club/position-group), `clubSummary`. `QueryError` for user-facing errors. |
| `src/server.ts` | 495 | `createServer()` registers 17 tools on `McpServer` with zod input schemas; handlers return human-readable text; `QueryError` → `isError` tool result. |

## Data flow

`index.ts` → `loadDataset()` (reads `data/kaggle/*.csv`) → `new SoccerDB(dataset)`
→ `createServer(db)` registers 17 tools → `connect(StdioServerTransport)`. Each tool
call resolves free-text team/competition names, runs a `SoccerDB` method, and formats
a text block. Tests use an in-memory transport pair (`tests/helpers.ts`) to exercise
the same path a client would.

## Tests

`tests/normalize.test.ts` (unit: normalisation, dates, CSV), `tests/queries.test.ts`
(SoccerDB behaviour against real data), `tests/server.test.ts` (end-to-end MCP tool
calls incl. 28 spec sample questions). 91 cases, all passing (`test_coverage=1.0`).
