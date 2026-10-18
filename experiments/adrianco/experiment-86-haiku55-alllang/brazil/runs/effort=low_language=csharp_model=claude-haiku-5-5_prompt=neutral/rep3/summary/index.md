# Summary: brazil · effort=low language=csharp model=claude-haiku-5-5 prompt=neutral · rep 3

- **Shape:** C# / .NET 10 MCP server (JSON-RPC 2.0 over stdio) with a hand-written RFC-4180 CSV reader and an in-memory LINQ query layer over Brazilian soccer datasets.
- **Structure:** 11 source files across Mcp / Data / Csv / Domain namespaces, plus 6 test files (36 test methods incl. 1 data-driven Theory) and a shared fixture.
- **Interfaces:** 0 HTTP routes, 6 MCP tools (search_matches, get_team_stats, head_to_head, get_standings, get_league_stats, search_players), 4 JSON-RPC methods, 1 CLI data-dir argument.
- **Notable:** No MCP SDK dependency — the protocol server, CSV parser, team-name normaliser and accent-folding are all implemented by hand with zero NuGet packages. Cross-file match de-duplication by fingerprint and a heuristic team-name alias/containment resolver handle the spec's name-variation requirement.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
