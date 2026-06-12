# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/index.ts | Process entrypoint — boots the MCP server | top-level `await createServer()` |
| src/server.ts | MCP server: tool registration + dispatch over stdio | `createServer()` |
| src/data/loader.ts | Reads & caches the seven kaggle CSVs | `loadAllData()`, `AllData` |
| src/data/normalizer.ts | Team-name canonicalization + fuzzy matching | `normalizeTeamName()`, `teamsMatch()` |
| src/tools/matches.ts | `find_matches` — filter matches by team/competition/season | `findMatches()` |
| src/tools/teams.ts | `get_team_stats` — aggregate W/L/D + goals for a team | `getTeamStats()` |
| src/tools/players.ts | `find_players` — FIFA player search/filter | `findPlayers()` |
| src/tools/headToHead.ts | `get_head_to_head` — H2H record between two teams | `getHeadToHead()` |
| src/tools/standings.ts | `get_standings` — table computed from match results | `getStandings()` |
| src/__tests__/acceptance.test.ts | 10 acceptance tests driving the live MCP server | 10 `it()` cases |
