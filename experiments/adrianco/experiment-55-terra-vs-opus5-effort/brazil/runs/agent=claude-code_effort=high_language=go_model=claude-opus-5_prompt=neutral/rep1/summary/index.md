# Architecture summary — brazilian-soccer-mcp (go)

*(run-summary skill not invoked as a subagent; this concise summary was produced inline.)*

## Layout

```
main.go              CLI entrypoint: stdio MCP server (default), -demo, -ask, -version
embed.go             go:embed of the six data/kaggle CSVs into the binary
internal/mcpsrv/     MCP surface — tool/resource/prompt registration + text formatting
  server.go          New(); 14 tools, 3 resources, 2 prompts; input/output structs
  format.go          human-readable formatting of every result type
  samples.go         catalogue of ~28 sample NL questions -> tool calls (backs -demo + tests)
internal/soccer/     domain: knowledge graph + queries (SDK-independent, pure Go)
  load.go            two-pass CSV loader; team-name resolution; duplicate-fixture merge
  model.go graph.go  Graph, Team, Match, Player nodes; finalize/indexing
  normalize.go aliases.go dates.go rivalry.go   name folding, date parsing, derbies
  query_match.go     SearchMatches, HeadToHead
  query_team.go      TeamStats (W/L/D, goals, home/away split)
  query_competition.go  Standings (computed table), Bracket (knockout)
  query_stats.go     AggregateStats, CompareSeasons
  query_player.go    SearchPlayers, PlayerProfile, ClubSquad (cross-dataset join)
```

## Design highlights

- **Clean separation**: `internal/soccer` is a self-contained domain library with no MCP
  dependency; `internal/mcpsrv` is a thin adapter that registers tools and formats output.
  Every tool returns both a text block (spec-shaped) and validated structured JSON.
- **Two-pass loader**: pass 1 learns which club bases are ambiguous across states; pass 2
  resolves names to canonical team IDs, builds match nodes, and merges duplicate fixtures
  that appear in more than one dataset. Handles state suffixes, accents, and the FIFA/match
  club-name mismatch.
- **Computed, not copied**: standings and champions are derived from raw match results;
  season-spill correction reassigns Jan/Feb league matches to the prior season (COVID 2020).
- **Honest gaps**: ambiguous team names are reported with candidates rather than guessed;
  FIFA 19 club coverage limits and the absence of goalscorer data are surfaced to the user.

## Tests

47 test functions across 3 packages (main, mcpsrv, soccer), including BDD-style feature
tests named per spec category (`TestFeatureMatchQueries`, `…TeamQueries`,
`…CompetitionQueries`, `…PlayerQueries`, `…StatisticalAnalysis`) plus a demo-answers-every-
question acceptance test and a query-performance test. All pass; 0 skipped. Coverage per
package: soccer 90.7%, mcpsrv 87.5%, main 52.1%.
