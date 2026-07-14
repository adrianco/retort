# Evaluation feedback on your previous attempt

A previous attempt is already in this directory. It did NOT pass an independent evaluation. Fix it.

## Requirements that must ALL be met
- [R1] Implements an MCP server (MCP protocol) exposing tools/handlers for the queries below  (verify: An MCP server entrypoint + registered tools/resources exist (server SDK usage, tool definitions).)
- [R2] Loads and uses the provided datasets in data/kaggle/ as the data source  (verify: Code reads the supplied CSVs (matches, FIFA players) rather than hardcoding or calling external APIs only.)
- [R3] Match query: find matches by team (home, away, or either)  (verify: A tool/function filters matches by team name.)
- [R4] Match query: filter by date range and/or season  (verify: Matches can be filtered by season/year or date range.)
- [R5] Match query: filter by competition (Brasileirao, Copa do Brasil, Libertadores)  (verify: Competition is a selectable filter spanning the provided competition datasets.)
- [R6] Team query: match history with win/loss/draw record and goals for/against  (verify: A tool returns aggregated W/L/D and goals for a team.)
- [R7] Player query: search players by name  (verify: A tool searches the FIFA player data by name.)
- [R8] Player query: filter players by nationality and/or club, with ratings/attributes  (verify: Players filterable by nationality or club, returning ratings.)
- [R9] Competition query: season standings calculated from match results  (verify: Standings (points/positions) are computed from matches, not hardcoded.)
- [R10] Statistical analysis: aggregate stats (e.g. avg goals/match, home vs away, biggest wins)  (verify: At least one aggregate statistic computed over the dataset.)
- [R11] Head-to-head records between two teams  (verify: A tool returns head-to-head W/L/D between two named teams.)
- [R12] Automated tests covering the query capabilities  (verify: A test suite exercises the query functions; tests execute (test_coverage > 0).)

## What went wrong last time
- The build/tests did not fully pass (status: failed, requirement_coverage 0.92).
- MCP server cannot start — server.run_stdio() is not a real SDK method
- get_team_stats W/L/D counts are wrong (double-counted from both perspectives)

Fix the existing code so every requirement above is met and the tests run and pass.