# Architecture summary

_The `run-summary` skill is not registered in this session; this is a concise hand-written substitute._

## Modules

- **cmd/main.go** — entrypoint. Loads `./data/kaggle`, prints match/player counts,
  then blocks forever on an empty channel. Does **not** start any server.
- **internal/models/models.go** — data structs: `Match`, `Player` (~40 attrs),
  `TeamStats`, `CompetitionResult`, `HeadToHead`, `BigWin`.
- **internal/store/loader.go** — `DataLoader` parses the 6 Kaggle CSVs with per-file
  column layouts; `normalizeTeamName` strips state suffixes and maps name variants.
- **internal/store/database.go** — query engine over loaded slices: match finders,
  team stats, head-to-head, standings, big wins, average goals, home win rate,
  player search by name/nationality/club, top/Brazilian players.
- **internal/server/server.go** — a natural-language query dispatcher (`parseQuery`
  keyword classifier → 14 `handleX` methods → `QueryResponse` JSON). **Never
  instantiated by main — unreachable dead code.**

## Flow

`main` → `store.LoadData` → `DataLoader.LoadAll` (6 CSVs) → prints counts → hangs.
The intended `server.ExecuteQuery(query) → handleQuery → db.*` path exists but is
never wired to any transport (no MCP, no CLI, no stdin loop).

## Gap vs. spec

The spec asks for an **MCP server**. The data + query layers are substantially built
and tested (store), but there is no MCP protocol, no tool registration, and the query
layer is not reachable from the binary.
