# Summary: language=csharp · model=sonnet-5 · prompt=bdd · rep 1

- **Shape:** C# / .NET 10 stdio MCP server (`ModelContextProtocol` SDK) over an in-memory store of Brazilian soccer CSVs, with a clean Core/Server/Tests split.
- **Structure:** 35 source `.cs` files (Core library + Server host + tools), 10 xUnit test classes (41 test methods), ~2,326 LOC.
- **Interfaces:** 12 MCP tools spanning all 5 required categories (match, team, player, competition, statistics); Core exposes 5 query services + normalization/parsing helpers, MCP-independent and unit-testable.
- **Notable:** Explicit de-duplication of overlapping Série A datasets to avoid double-counting; collision-aware team-name normalization (keeps state suffixes only where the base name genuinely collides); standings computed live from matches; `NA`/postponed-match rows skipped defensively. BDD prompt followed: Given/When/Then behaviour-named tests (`test_given_..._when_..._then_...`).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
