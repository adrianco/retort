# Run Summary: brazilian-soccer-mcp (go, opus-5-5, neutral, effort=low) rep2

## Surface

A single-binary Go MCP (Model Context Protocol) stdio server answering natural-language
questions about Brazilian soccer from six bundled Kaggle CSV datasets (5 match files +
the FIFA player file). It exposes 13 JSON-RPC tools covering match search, head-to-head,
team records, league standings, rankings, season comparison, derbies, player search and
cross-dataset team profiles.

See [`modules.md`](modules.md) and [`interfaces.md`](interfaces.md).

## Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| `main.go` | CLI entry: load data, run stdio server or one-off `-call` | `main`, `envOr` |
| `mcp.go` | JSON-RPC 2.0 / MCP transport + the 13-tool registry | `Tools`, `(*DB).Handle`, `(*DB).Serve`, `(*DB).CallTool` |
| `data.go` | CSV loading, team-name normalization, date parsing, data model | `LoadDB`, `Match`, `Player`, `DB`, `TeamKey`, `Fold`, `ParseDate`, `NormalizeCompetition` |
| `query.go` | All query/aggregation logic and text formatting | `FindMatches`, `HeadToHead`, `TeamRecord`, `Standings`, `TeamRankings`, `CompareSeasons`, `FindPlayers`, `TeamProfile` |
| `server_test.go` | Unit + integration + sample-question tests | 13 `Test*` functions |

## Interfaces

MCP tools (via `tools/call`): `search_matches`, `head_to_head`, `team_record`,
`standings`, `team_rankings`, `compare_seasons`, `team_competitions`, `derbies`,
`search_players`, `player_details`, `players_by_club`, `team_profile`, `dataset_overview`.

JSON-RPC methods: `initialize`, `ping`, `tools/list`, `tools/call` (+ notifications ignored).

CLI: `brsoccer [-data DIR]` (stdio server) and `brsoccer -call <tool> '<json-args>'`.

## Flow

`main` → `LoadDB(dir)` reads 6 CSVs into `[]*Match` / `[]*Player` with normalized
team keys → `Serve` scans newline-delimited JSON-RPC from stdin → `Handle` dispatches
`tools/call` to `CallTool` → each tool's handler calls a `query.go` method that filters
`db.Matches`/`db.Players` (with cross-source de-duplication) and returns formatted text.

## Notable design points

- Cross-source **de-duplication** (`dedupKey` + `sameFixture`) so the three overlapping
  Serie A files don't double-count (verified: 2018 Serie A → exactly 380 matches).
- Accent-folding + alias tables normalize team names across the datasets' naming schemes.
- Standings computed from a single best source per season to avoid overlap corruption.
