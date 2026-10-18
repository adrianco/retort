# Architecture Summary

Brazilian Soccer MCP server, TypeScript / ESM, Node ≥18. ~1018 LOC across 8 source modules, 5 test files (48 tests). Dependencies: `@modelcontextprotocol/sdk`, `zod` (+ typescript, vitest, @types/node dev).

## Modules (`src/`)

| Module | Role |
|--------|------|
| `index.ts` | Entry point. Lazily loads the dataset, builds the server, serves over stdio (`StdioServerTransport`). `BRAZIL_SOCCER_DATA_DIR` overrides the CSV directory. Logs to stderr (stdout is the MCP channel). |
| `server.ts` | `createServer(getDataset)` — registers 7 MCP tools with zod input schemas: `search_matches`, `team_record`, `head_to_head`, `standings`, `search_players`, `club_squad_summary`, `match_statistics`. Lazy `getDataset` so CSVs parse on first tool call. |
| `queries.ts` | Pure query layer over an in-memory `Dataset`: `searchMatches`, `teamRecord`, `headToHead`, `standings` (3-1-0 points, computed from results), `searchPlayers`, `clubSummary`, `matchStatistics` (avg goals, home/draw/away rates, biggest wins). |
| `loader.ts` | Reads all 6 Kaggle CSVs via per-file column mappings (`MATCH_SOURCES`), normalizes to the `Match`/`Player` model, de-duplicates cross-file fixtures (date±1 / competition / score / shared leading word), loads FIFA players. |
| `normalize.ts` | Text/team-name folding (strip accents, state suffixes, parens), whole-word containment matching, multi-format date parser (ISO, `DD/MM/YYYY`, datetime). |
| `csv.ts` | Minimal RFC-4180 CSV parser: quoted fields, embedded commas/newlines, CRLF, BOM. |
| `format.ts` | Human-readable text formatters for each tool result. |
| `model.ts` | `Match`, `Player`, `Dataset` interfaces. |

## Flow

`index.main()` → `createServer(getDataset)` → stdio transport. On first tool call, `loadDataset()` parses the 6 CSVs → `{matches, players}` held in memory → query functions filter/aggregate → formatters render text → returned as MCP text content.

## Data

All 6 CSVs present under `data/kaggle/` and wired into `MATCH_SOURCES` + `loadPlayers`: Brasileirao_Matches, novo_campeonato_brasileiro, Brazilian_Cup_Matches, Libertadores_Matches, BR-Football-Dataset (match files), fifa_data (players). `loader.test.ts` loads the real files and asserts counts (≥18000 players, 380–385 Serie A 2019 fixtures after dedup, >1200 Libertadores).
