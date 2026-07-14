# Summary: language=java_model=sonnet_prompt=ATDD · rep 1

- **Shape:** Java MCP server (modelcontextprotocol SDK, stdio transport) over in-memory CSV-loaded soccer data, using Apache Commons CSV.
- **Structure:** 9 main modules (1 server + 4 services + 4 models), 6 test files (5 acceptance + 1 unit), 51 tests.
- **Interfaces:** 6 MCP tools (findMatches, getTeamStats, findPlayers, getStandings, getHeadToHead, getStatistics); no HTTP/CLI.
- **Notable:** ATDD prompt visibly followed — acceptance tests exercise only public tool methods in domain language, with finer-grained unit tests under the normalizer. Thoughtful data dedup (novo_campeonato limited to 2003–2011) and team-name normalization for the spec's naming-variation requirement.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
