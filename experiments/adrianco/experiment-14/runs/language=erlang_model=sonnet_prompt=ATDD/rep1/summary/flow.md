# Flow

```mermaid
sequenceDiagram
    Client->>soccer_mcp.erl: {"method":"tools/call","params":{"name":"find_matches","arguments":{"team":"Flamengo"}}}
    soccer_mcp.erl->>soccer_tools.erl: call(<<"find_matches">>, Args)
    soccer_tools.erl->>soccer_data.erl: find_matches_all(Criteria)
    soccer_data.erl->>soccer_data.erl: persistent_term:get(soccer_matches)
    soccer_data.erl-->>soccer_tools.erl: [Match]
    soccer_tools.erl->>soccer_tools.erl: sort by date desc, sublist(limit), format_match/1
    soccer_tools.erl-->>soccer_mcp.erl: {ok, <<json>>}
    soccer_mcp.erl-->>Client: {"result":{"content":[{"type":"text","text":<json>}]}}
```

A `tools/call` request is decoded by `soccer_mcp:handle_message/1`, dispatched to `soccer_tools:call/2`, which converts JSON args to an atom-keyed criteria map and queries the in-memory dataset via `soccer_data:find_matches_all/1`. Matches are loaded once at startup (`soccer_data:init/0`) into `persistent_term` for zero-copy reads; queries are linear `lists:filter` scans. Results are sorted, truncated to `limit` (default 20), JSON-encoded, and wrapped in an MCP `content` text block. Team matching normalizes the search term (strips state suffixes like `-RJ`) and does case-insensitive substring matching. Notable: no pagination cursors (offset-less `limit` only), all queries are full O(n) scans over the dataset, and individual CSV parse failures are swallowed (`catch _:_ -> []`) so a malformed file silently yields zero rows.
