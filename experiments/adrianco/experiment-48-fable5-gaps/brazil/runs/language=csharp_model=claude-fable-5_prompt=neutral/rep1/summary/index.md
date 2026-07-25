# Architecture Summary — Brazilian Soccer MCP Server (C#)

> `run-summary` skill not available in this session; this summary was written
> directly during evaluation.

## Solution layout

Three-project .NET solution (`BrazilianSoccerMcp.slnx`):

- **`src/BrazilianSoccer.Core`** — the library holding all data + query logic.
- **`src/BrazilianSoccer.Server`** — thin stdio executable (`Program.cs`) wiring
  the data store into the MCP server loop.
- **`tests/BrazilianSoccer.Tests`** — xUnit suite (57 test methods).

## Modules

| File | Role |
|------|------|
| `Csv.cs` | Minimal RFC-4180-ish CSV parser (`ParseFile`, `HeaderMap`). |
| `Models.cs` | `Match`, `Player`, `TeamRecord` records with derived props (`Points`, `Margin`, `WinRate`). |
| `TeamNames.cs` | Team-name normalization → canonical key; accent folding + state-suffix stripping + alias table. |
| `DataStore.cs` | Loads all 6 Kaggle CSVs into a unified in-memory model; dedups overlapping matches on (date±1d, home, away) and merges extra columns. |
| `QueryService.cs` | All query capabilities, each returning an LLM-friendly text block. |
| `SoccerTools.cs` | Declares 9 MCP tools with JSON schemas, binding each to a `QueryService` method. |
| `McpServer.cs` | JSON-RPC 2.0 over newline-delimited JSON (stdio): `initialize`, `tools/list`, `tools/call`, `ping`, empty `resources/prompts` lists. |
| `Program.cs` | Entry point: locates `data/kaggle`, verifies Unicode normalization works, loads store, serves. |

## MCP tools exposed

`search_matches`, `head_to_head`, `get_team_stats`, `get_standings`,
`search_players`, `get_player`, `get_competition_stats`, `get_biggest_wins`,
`list_competitions`.

## Data flow

`Program` → `DataStore.Load(dataDir)` reads/dedups CSVs → `QueryService(store)`
→ `SoccerTools.Build(q)` → `McpServer` serves JSON-RPC; each `tools/call`
dispatches to a tool handler → `QueryService` method → formatted text result.

## Notable engineering

- Cross-dataset match deduplication with a ±1-day window (UTC vs local kickoff).
- Team-name canonicalization with an explicit display-override table for
  ambiguous clubs (Atlético-MG, Athletico-PR, Vasco, …).
- Multiple date-format parsing (ISO, Brazilian `dd/MM/yyyy`, with/without time).
- Accent-insensitive matching via Unicode `FormD` folding, with a startup guard
  that aborts if invariant globalization would break normalization.
