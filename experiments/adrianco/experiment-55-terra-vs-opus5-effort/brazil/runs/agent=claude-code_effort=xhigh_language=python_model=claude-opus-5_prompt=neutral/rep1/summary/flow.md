# Flow

Representative flow: an LLM asks for the head-to-head between two clubs via the MCP tool `head_to_head`. This exercises the full stack — name resolution, the cached graph, index lookup, aggregation and rendering.

```mermaid
sequenceDiagram
    Client->>server.py: call head_to_head(team_a="Flamengo", team_b="Fluminense")
    server.py->>tools.py: call_tool("head_to_head", args)
    tools.py->>graph.py: load_knowledge_graph()
    Note over graph.py: cached; rebuilds only if CSV size/mtime changed
    graph.py-->>tools.py: KnowledgeGraph
    tools.py->>queries.py: head_to_head(graph, team_a, team_b)
    queries.py->>queries.py: resolve_team() x2 (registry fuzzy match)
    queries.py->>queries.py: search_matches() via matches_by_team index
    queries.py-->>tools.py: HeadToHead (wins/draws/goals aggregated)
    tools.py->>formatting.py: format_head_to_head(graph, record)
    formatting.py-->>tools.py: rendered text
    tools.py-->>server.py: ToolResult(text, data)
    server.py-->>Client: text answer
```

On first call `load_knowledge_graph()` builds the graph once: `read_all_match_rows()` parses all five match CSVs into `ParsedRow`s (per-file parsers, cup-round naming), `load_matches()` runs the two-pass `TeamRegistry` to resolve club spellings, `deduplicate()` merges cross-source duplicates (Serie A appears in three files) by (competition, ordered club pair) plus season/date proximity, `load_players()` reads FIFA rows and links clubs restricted to Serie-A teams, then `KnowledgeGraph` materialises nodes, typed edges and hot-path dict indexes. The result is cached per process, keyed on each CSV's size+mtime.

Per query: `call_tool` strips `None` args, dispatches to the tool handler, which calls the query function. `resolve_team` does forgiving fuzzy matching (accents, state suffixes, nicknames), the query picks the cheapest index (`matches_by_team` here), aggregates into a dataclass, and `formatting` renders the TASK.md answer layout. Both a text string and a JSON `data` payload are returned.

Notable characteristics (factual, not judgments):
- Errors are values, not exceptions at the boundary: `TeamNotFound`/`CompetitionNotFound`/`TypeError`/`ValueError` are caught in `call_tool` and returned as helpful messages with suggestions, so a mistaken LLM can retry.
- Argument handling is deliberately forgiving: seasons accept int or str, competitions accept many aliases, clubs accept raw/suffixed/nickname spellings.
- Entirely in-memory and synchronous; no database, no network (optional external APIs in TASK.md are not used). The MCP server (`server.py`) is the only module touching the `mcp` SDK.
- Cup champions are derived from final aggregate scores; the code explicitly declines to name a champion when a final was decided on penalties (not in the data) or when the season's knockout rounds are incomplete.
- Data-coverage limits are surfaced rather than hidden: player queries for unlicensed FIFA-19 clubs (Flamengo, Palmeiras, ...) return an explanatory note; top-scorer/lineup queries are documented as underivable.
