# Interfaces

## MCP protocol (JSON-RPC 2.0 over stdio)

Methods handled by `server/dispatch`:

- `initialize` — negotiates protocolVersion, advertises `tools` capability, serverInfo `brazilian-soccer 1.0.0`.
- `ping` — `{}`.
- `tools/list` — returns the 6-tool `catalog`.
- `tools/call` — validates args against the tool's `inputSchema`, runs the query, returns JSON text content.
- notifications (no `id`) return nil; unknown methods → `-32601`; bad args → `-32602`.

## Tools (catalog)

| Tool | Purpose | Key args |
|------|---------|----------|
| `matches` | Fixtures/scores/dates, newest first | team_name, opponent, venue, season, competition, source, start, end, stage, derby, limit, offset |
| `team_profile` | Team record + head-to-head + by-competition/by-season + FIFA roster | team_name (required), venue, season, … |
| `players` | FIFA players sorted by overall | name, nationality, club, position, limit, offset |
| `standings` | League table computed from played fixtures | competition, season, venue, rank_by (points/goals/win_rate) |
| `statistics` | Fixture counts, avg total goals, home win rate; optional group_by | competition, season, group_by (competition/season) |
| `biggest_wins` | Completed matches by absolute goal margin | competition, season, … |

## Data schema (in-memory DB from `load-db`)

- `:matches` — normalized fixtures: `{:date :season :competition :home :away :home-id :away-id :home_goal :away_goal :round :stage :source :details}`.
- `:sources` — per-file raw fixtures (every original CSV row stays queryable).
- `:players` — `{:id :name :club :position :overall :nationality :attributes}` sorted by overall.
