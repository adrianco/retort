# Architecture — BrazilianSoccerMcp (C#, .NET 10)

Hand-rolled MCP server over stdio; no external MCP SDK. Clean layering with pure query logic.

## Modules (`src/BrazilianSoccerMcp/`)

| File | Responsibility |
|------|----------------|
| `Program.cs` | Entry point: resolves `data/kaggle`, loads datasets once, wires tools → `McpServer`, serves MCP over stdio (UTF-8, stderr for diagnostics). |
| `McpServer.cs` | Minimal JSON-RPC 2.0 over newline-delimited stdio. Handles `initialize`, `ping`, `tools/list`, `tools/call`; notifications get no response; tool errors returned as `isError` results, protocol errors as JSON-RPC codes. |
| `SoccerTools.cs` | 7 MCP tools (`search_matches`, `team_record`, `head_to_head`, `standings`, `match_statistics`, `search_players`, `brazilian_club_summary`) with JSON input schemas + spec-format plain-text output. |
| `SoccerQueries.cs` | Pure query engine over the in-memory dataset: match search, team W/L/D records, head-to-head, season standings (win 3/draw 1), aggregate statistics, player search, squad summaries. |
| `DataLoader.cs` | Loads all 6 Kaggle CSVs into a unified `Match` list + `Player` list; normalizes competitions, de-duplicates fixtures, handles multiple date/goal formats. |
| `TeamNames.cs` | Team-name normalization: diacritics removal, state-suffix stripping, fuzzy key matching. |
| `Csv.cs` | Lightweight CSV reader (quoted fields, header map). |
| `Models.cs` | `Match`, `Player` records; `Venue` enum. |

## Data flow

`Program` → `DataLoader.Load(dataDir)` → `SoccerDataset` (in-memory) → `SoccerQueries` → `SoccerTools` handlers → `McpServer` → stdio JSON-RPC.

## Tests (`tests/BrazilianSoccerMcp.Tests/`, xUnit)

~40 Fact/Theory cases across `SoccerQueriesTests`, `McpServerTests`, `DataLoaderTests`, `CsvTests`, `TeamNameTests`, using a synthetic `TestData` dataset. Exercise all query functions and the full MCP request/response loop. No skipped tests.
