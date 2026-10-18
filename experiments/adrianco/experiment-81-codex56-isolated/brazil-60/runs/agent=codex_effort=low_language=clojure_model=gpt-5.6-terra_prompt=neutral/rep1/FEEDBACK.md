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
- standings computes factually wrong tables: clubs collapse by name, no season default

## Factual accuracy — your answers were checked against known results
- **2019 Série A: Flamengo's record** — expected 28W-6D-4L (= 38 played, 90 points), got row figures [40, 712742980561565, 240, 1371, 1061, 309, 926, 377, 1199, 40, 712742980561565, 240, 1371, 1061, 309, 926, 377, 1199, 40, 712742980561565, 240, 1371, 1061, 309, 926, 377, 1199, 47, 7317073170732, 101, 680, 443, 116, 410, 193, 604, 41, 951219512195124, 127, 643, 374, 111, 410, 172, 493, 41, 56479217603912, 120, 630, 425, 119, 409, 170, 518, 40, 97560975609756, 116, 620, 417, 126, 410, 168, 528, 47, 31182795698925, 86, 614, 399, 110, 372, 176, 542, 44, 73684210526316, 103, 613, 361, 107, 380, 170, 491, 39, 268292682926834, 105, 588, 477, 144, 410, 161, 511, 41, 397849462365585, 108, 570, 383, 110, 372, 154, 466, 41, 77631578947368, 79, 460, 329, 98, 304, 127, 391, 34, 13173652694611, 81, 423, 407, 139, 334, 114, 366, 30, 263157894736842, 90, 366, 371, 122, 304, 92, 328, 31, 57894736842105, 78, 366, 397, 130, 304, 96, 313, 29, 49152542372881, 77, 338, 386, 131, 295, 87, 311, 31, 57894736842105, 80, 332, 355, 102, 266, 84, 280, 26, 41509433962264, 77, 287, 359, 118, 265, 70, 261, 32, 727272727272734, 55, 271, 296, 93, 220, 72, 243, 31, 5263157894737, 51, 228, 243, 80, 190, 59, 200, 30, 526315789473678, 48, 222, 281, 84, 190, 58, 233, 28, 21978021978022, 64, 217, 200, 67, 182, 51, 189, 36, 11111111111111, 34, 190, 170, 58, 144, 52, 158, 29, 166666666666668, 37, 163, 172, 65, 144, 42, 121, 25, 657894736842106, 40, 157, 219, 73, 152, 39, 142, 33, 9622641509434, 39, 147, 125, 31, 106, 36, 145, 21, 52777777777778, 40, 133, 217, 73, 144, 31, 113, 28, 947368421052634, 27, 93, 87, 27, 76, 22, 89, 26, 31578947368421, 18, 78, 119, 38, 76, 20, 77, 25, 0, 26, 77, 69, 25, 68, 17, 56, 25, 0, 12, 69, 130, 45, 76, 19, 66, 20, 58823529411765, 24, 66, 97, 30, 68, 14, 59, 21, 5263157894737, 8, 32, 58, 22, 38, 8, 24, 21, 5263157894737, 7, 31, 69, 23, 38, 8, 45, 18, 42105263157895, 10, 31, 48, 21, 38, 7, 26, 10, 52631578947368, 11, 23, 57, 23, 38, 4, 18].
  2019 Série A is a 20-team double round-robin: every club plays exactly 38 and Flamengo won on 90 points, as the task's own worked example states. Roughly double those figures means the five match files were concatenated without reconciling them — the same fixture appears in two or three of them, and 23,954 rows is exactly their sum. Deduplicate on (date, home, away) allowing a one-day difference: sources disagree on local kick-off vs UTC date.
- **2019 Série A: all 20 clubs present** — expected 20 of 20, got 19 of 20 (1 Atlético/Athletico row(s), expected 2).
  The 2019 Brasileirão Série A had exactly these 20 clubs. Missing ones usually mean the table was truncated for display — return the whole table — or that a club's name variant (accents, the -SP/-MG state suffix) was not normalised and so its matches were dropped.

Fix the existing code so every requirement above is met and the tests run and pass.