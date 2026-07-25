# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Single-file HTTP server: data models, CSV loaders, query functions, REST handlers | `main()`, `SoccerServer`, `NewSoccerServer()`, `LoadData()`, `matchesHandler`, `playersHandler`, `teamStatsHandler`, `headToHeadHandler`, `standingsHandler`, `biggestWinsHandler`, `teamRecordHandler`, `healthHandler` |
| main_test.go | Unit + handler tests over synthetic in-memory data | 23 `Test*` functions |
| go.mod / go.sum | Module `soccer-mcp`, single dep `github.com/google/uuid` | — |
| data/kaggle/*.csv | 6 provided datasets (5 match CSVs + fifa_data.csv) | — (read at runtime) |

Note: despite the module name `soccer-mcp`, there is **no MCP protocol** implementation — this is a plain `net/http` REST server.
