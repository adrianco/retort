# Architecture summary

_The `run-summary` skill is not registered in this session; this is a concise
hand-written substitute. Regenerated after the REPAIR run — the previous version
described the pre-repair state (no MCP server) and was stale._

## Modules

- **cmd/main.go** — entrypoint AND MCP wiring. Loads `./data/kaggle`, prints
  match/player counts, constructs `mcp.NewServer`, registers **17 tools** via
  `mcp.AddTool` (find_matches_by_team/…/compare_teams), then serves over
  `mcp.StdioTransport`. Also holds the `format*Text` presentation helpers.
- **internal/models/models.go** — data structs: `Match`, `Player` (~45 attrs),
  `TeamStats`, `CompetitionResult`, `HeadToHead`, `BigWin`, `QueryResult`.
- **internal/store/loader.go** — `DataLoader` parses the 6 Kaggle CSVs with
  per-file column layouts; `normalizeTeamName` strips state suffixes and maps
  name variants.
- **internal/store/database.go** — query engine over the loaded slices: match
  finders (team / teams / season / competition / date-range), team stats,
  head-to-head, standings, big wins, average goals, home win rate, player search
  by name / nationality / club, top / Brazilian players.
- **internal/server/server.go** — `SoccerServer` thin façade delegating to
  `store.Database`, plus a **second copy** of the `format*Text` helpers used only
  by `server_test.go`.

## Flow

`main` → `store.LoadData` → `DataLoader.LoadAll` (6 CSVs) → `server.NewSoccerServer`
→ `addTools(mcpServer, soccerServer)` → `mcpServer.Run(StdioTransport)`. Each MCP
tool handler calls a `SoccerServer` method, which delegates to `store.Database`, and
formats the result as `mcp.TextContent`.

## Status vs. spec

The central R1 gap flagged in FEEDBACK.md is now closed: a real MCP server
(`github.com/modelcontextprotocol/go-sdk` v1.6.1) with registered tool definitions
is wired to the binary. All 12 pinned requirements are implemented; build + `go test`
pass (test_coverage=0.639, defect_rate=1.0). Remaining issues are quality, not
conformance — see `findings.jsonl`.
