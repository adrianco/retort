# Architecture summary

Brazilian Soccer MCP server (TypeScript, ESM, `@modelcontextprotocol/sdk` + `zod`).
A clean layered design: CSV parsing → typed dataset → query engine → MCP tools.

## Modules (`src/`)

| File | Role |
|------|------|
| `csv.ts` | Minimal CSV parser (`parseCsv` → `CsvRow[]`). |
| `dates.ts` | Multi-format date parsing (`parseDate`, `normalizeDateBound`, `daysBetween`) handling ISO, Brazilian `DD/MM/YYYY`, and datetime-with-time. |
| `teams.ts` | Team-name normalization: curated `CLUBS`, aliases, `parseTeamName`, `RIVALRIES`, `findRivalry`, `normalizeText` (accent-insensitive). |
| `data.ts` | `loadDataset` — reads all 6 Kaggle CSVs into one in-memory graph. `Loader` maps every source onto a common `Match` shape, de-duplicates cross-file fixtures (`dedupe`), folds stateless team-name variants, and loads FIFA players. |
| `queries.ts` | `SoccerKnowledgeBase` — the query engine: `findMatches`, `headToHead`, `teamRecord`, `teamRankings`, `standings`, `bracket`, `cupFinals`, `biggestWins`, `competitionStats`, `compareSeasons`, `derbies`, `searchPlayers`, `getPlayer`, `playersByClub`, `teamProfile`. Standings/titles computed from match results. |
| `format.ts` | Text formatting of query results for LLM-friendly tool responses. |
| `server.ts` | `createServer(kb)` — registers 17 MCP tools (search_matches, head_to_head, team_record, team_profile, team_rankings, find_team, league_standings, cup_bracket, cup_finals, list_competitions, biggest_wins, competition_stats, compare_seasons, derby_matches, search_players, get_player, players_by_club). Each wrapped in a `guard` that returns tool errors rather than throwing. |
| `index.ts` | Entrypoint — loads data, serves tools over stdio (`StdioServerTransport`). Supports `--data-dir` / `BRAZIL_SOCCER_DATA_DIR`. |

## Data flow

`index.ts` → `SoccerKnowledgeBase.load()` → `loadDataset()` reads `data/kaggle/*.csv`
→ builds `canonical` (de-duplicated) match list + teams + players → `createServer(kb)`
registers tools → tool call → `kb.<query>()` → `format.ts` → text response.

## Tests (`tests/`, 51 tests, 0 skipped)

- `csv-dates.test.ts`, `data.test.ts`, `teams.test.ts` — unit tests of parsing/loading/normalization.
- `queries.test.ts` — 22 tests exercising every query category (matches, teams, competitions, statistics, players).
- `server.test.ts` — MCP tool discovery, 20+ sample spec questions, cross-file queries, error handling.
- `stdio.test.ts` — spawns the real entrypoint and talks MCP over stdio as a host would (acceptance-level).
