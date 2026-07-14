# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Process entrypoint; builds MCP server over stdio | `main()` |
| internal/server/setup.go | Loads data and registers the 6 MCP tools | `RegisterTools(dataDir)` |
| internal/data/loader.go | CSV loaders + name/date/number normalization | `LoadAll()`, `NormalizeName()` |
| internal/data/models.go | Domain structs for matches and players | `Match`, `Player` |
| internal/tools/matches.go | `find_matches` tool (team/date/competition/season filters) | `FindMatchesTool()` |
| internal/tools/teams.go | `get_team_stats` tool (W/L/D, goals, win rate) | `GetTeamStatsTool()` |
| internal/tools/players.go | `find_players` tool (name/nationality/club/position) | `FindPlayersTool()` |
| internal/tools/headtohead.go | `get_head_to_head` tool between two teams | `GetHeadToHeadTool()` |
| internal/tools/standings.go | `get_standings` tool (points computed from matches) | `GetStandingsTool()` |
| internal/tools/stats.go | `get_statistics` tool (biggest_wins, avg_goals, home/away records) | `GetStatisticsTool()` |
| acceptance_test.go | Black-box acceptance suite exercising tools via MCP protocol | 10 test functions |
