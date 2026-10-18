# Architecture Summary: BrazilianSoccerMcp (C#, .NET 10)

A stdio MCP (Model Context Protocol) server over the six Kaggle CSV datasets.

## Layers

- **`Program.cs`** — entrypoint. Resolves the data directory (arg → `BRAZILIAN_SOCCER_DATA`
  → `./data/kaggle`), loads the dataset once, wires services into a `ToolRegistry` + `McpServer`,
  then runs a line-oriented JSON-RPC read loop on stdin/stdout (UTF-8, diagnostics to stderr).

- **`Mcp/`** — protocol layer.
  - `McpServer` — JSON-RPC 2.0 dispatch: `initialize`, `ping`, `tools/list`, `tools/call`;
    notifications get no reply; parse/invalid-request/method-not-found/invalid-params errors.
  - `ToolRegistry` — the 7 tools (`search_matches`, `team_stats`, `head_to_head`, `standings`,
    `league_stats`, `search_players`, `club_player_summary`): JSON input schemas + argument
    parsing/validation + dispatch to services.
  - `Formatting` — renders service records to human-readable text content.

- **`Services/`** — query logic.
  - `MatchService` — `Search` (team/opponent/venue/season/competition/date-range/round),
    `TeamStats` (W/L/D + goals), `HeadToHead`, `Standings` (3/1/0 points, computed from results),
    `LeagueStats` (goals/match, home/draw/away rates, biggest wins).
  - `PlayerService` — `Search` (name/nationality/club/position/min-overall) and `ClubSummaries`.

- **`Data/`** — ingestion. `CsvParser` (quoted-field CSV reader), `Field` (typed cell accessors),
  `DatasetLoader` (per-file readers for all 5 match files + FIFA players, with cross-file
  de-duplication in a ±3-day window), `Dataset` (in-memory match + player lists + load reports).

- **`Domain/`** — `Models` (`Match`, `Player`, outcomes), `TeamRef` (name normalisation +
  state-suffix handling), `TextFolding` (accent/case-insensitive matching), `Competitions`
  (canonical names + fragment resolution).

## Data flow

CSV files → `DatasetLoader` (parse, normalise, de-dupe) → `Dataset` → `MatchService`/`PlayerService`
→ `ToolRegistry` (validate args) → `Formatting` → `McpServer` JSON-RPC result.

## Tests

47 xUnit tests across 6 files (CsvParser, DatasetLoader, MatchService, McpServer, PlayerService,
TeamRef), written as Given/When/Then scenarios. `test_coverage=1.0` — build + all tests pass.
