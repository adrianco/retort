# Architecture Summary

**Surface:** An MCP server (stdio transport) that answers natural-language questions
about Brazilian soccer — matches, teams, players, competitions, standings and
statistics — computed from six provided Kaggle CSVs.

**Shape:** Clean four-layer split — `csv.ts` (parsing) → `data.ts` (load + normalize +
de-dup into a `Dataset`) → `queries.ts` (`SoccerKB` aggregation) → `tools.ts` (15 MCP
tools rendering plain-text answers) → `server.ts` (registration + stdio transport).
`teams.ts` provides team-name folding/resolution used throughout.

**Notable:** Tools far exceed the spec's minimum (derbies, knockout brackets, season
comparison, per-venue ranking, player profiles). Data is loaded from real CSVs, not
hardcoded; standings and records are computed, not stored. Unknown-entity errors are
surfaced as readable MCP `isError` text.

See [`modules.md`](modules.md) and [`interfaces.md`](interfaces.md).
