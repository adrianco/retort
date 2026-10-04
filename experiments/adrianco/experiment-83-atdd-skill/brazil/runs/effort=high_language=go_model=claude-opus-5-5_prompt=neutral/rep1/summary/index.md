# Architecture Summary — brazilian-soccer-mcp (go, opus-5.5, neutral prompt, high effort)

A single-package Go program (`module brsoccer`, **stdlib only**, no external deps). It
implements the Model Context Protocol server from scratch over JSON-RPC 2.0 / stdio.

## Modules

| File | Responsibility |
|------|----------------|
| `main.go` | Entry point. `serve` (stdio MCP, default), `tools` (list), `call TOOL JSON` (one-shot). Data dir via `-data`, `$BRSOCCER_DATA`, or `./data/kaggle`. |
| `mcp.go` | MCP/JSON-RPC server: `initialize`, `ping`, `tools/list`, `tools/call`, empty `resources`/`prompts` listings, batch support, notification handling. Serialised writes. |
| `data.go` | `LoadStore` reads all 6 Kaggle CSVs into an in-memory `Store`. Normalises 5 match files into one `Match` type, **de-duplicates** cross-file copies (same comp/teams, kick-off within 36h; source-priority ordering), loads FIFA players, maps FIFA Brazilian clubs to match teams. Multi-format date + goal parsing. |
| `normalize.go` | `TeamRegistry` — team-name folding (accent/cedilla strip), state-suffix handling (`Palmeiras-SP`), alias merging, fuzzy resolution weighted by match count. |
| `matches.go` | `MatchFilter`/`Filter`, `Record` (W/L/D, GF/GA, points), `Standings` computed from results, `HeadToHead`, `Summarise` aggregates, `Ties`/knockout stage logic, derby naming. |
| `players.go` | `PlayerFilter`/`FilterPlayers` (name, nationality, club, position, rating), player sorting, fuzzy name search, top-skill extraction. |
| `tools.go` | 14 MCP tools wiring the above into text responses (see below) + arg parsing helpers and the `CallTool` dispatcher. |

## Registered tools (14)

`search_matches`, `head_to_head`, `team_record`, `team_overview`, `standings`,
`rank_teams`, `biggest_wins`, `competition_stats`, `knockout_bracket`, `search_players`,
`player_profile`, `club_squads`, `find_team`, `dataset_info`.

## Tests

`data_test.go`, `normalize_test.go`, `matches`/`tools_test.go`, `mcp_test.go`. The centrepiece
is `TestSampleQuestions` — 30+ natural-language questions (the spec's examples) run through
`CallTool` with content assertions **and** the spec's 2s/5s response-time limits.
`TestBinaryOverStdio` exercises the real compiled binary over stdio (skipped only in `-short`).
test_coverage=0.857, defect_rate=1.0 (build + tests pass).
