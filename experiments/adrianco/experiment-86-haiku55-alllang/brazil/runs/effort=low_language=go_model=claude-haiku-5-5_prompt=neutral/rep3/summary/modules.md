# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Program entry: parse `-data` flag, load dataset, wire Handler to Server, serve MCP over stdin/stdout | `main()`, `serverVersion` |
| mcp.go | Minimal JSON-RPC 2.0 / MCP server over stdio (initialize, ping, tools/list, tools/call) | `Server`, `Serve()`, `Request`, `Response`, `RPCError`, `Tool` |
| tools.go | Tool catalogue and text formatting; maps each MCP tool to a Dataset query | `Tools()`, `Handler`, `Handler.Call()` |
| loader.go | Reads the six Kaggle CSVs into one de-duplicated `Dataset`; per-file parsers | `LoadDataset()`, `Dataset`, `Match`, competition consts |
| matches.go | Match queries: filter, team record, head-to-head, standings, aggregates, biggest wins | `MatchFilter`, `FindMatches()`, `TeamRecord()`, `HeadToHead()`, `Standings()`, `Aggregate()`, `BiggestWins()`, `Record`, `StandingRow`, `LeagueStats` |
| players.go | FIFA player model, parsing and search | `Player`, `PlayerFilter`, `SearchPlayers()`, `positionMatches()`, `ClubAverageOverall()` |
| team.go | Team-name normalization (accent/noise stripping, state suffix, token matching) | `TeamName`, `ParseTeam()`, `stripAccents()`, `TeamName.Matches()`, `TeamName.Key()` |
| loader_test.go | CSV loading, de-dup, date/goal parsing tests | 3 test functions |
| matches_test.go | Match filter, record, head-to-head, standings, aggregate tests | 6 test functions |
| mcp_test.go | JSON-RPC dispatch / protocol tests | 2 test functions |
| players_test.go | Player search and position-group tests | 2 test functions |
| team_test.go | Team-name normalization and matching tests | 1 test function |
| testhelpers_test.go | Shared test fixtures/helpers | (helpers, no test funcs) |

Non-source files present: `go.mod`, `README.md`, `brazilian-soccer-mcp-guide.md`, `prompts.txt`, `data/` (Kaggle CSVs), plus harness artifacts (`TASK.md`, `scores.json`, `stack.json`, `_meta.json`, logs) — not summarized.
