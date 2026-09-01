Port the FunkyGibbon MCP client to {{language}} by EXTENDING the existing
the-goodies repository, which is ALREADY CHECKED OUT in this directory. Do not
clone it — you are working inside it.

Read funkygibbon-mcp-port-guide.md in full first. Then study the protocol spec
(inbetweenies/PROTOCOL.md) and the two reference clients — the Python
`blowing-off` (including blowingoff/mcp/server.py) and the TypeScript
`kittenkong` (rolandcanyon-cmd/the-goodies-typescript). Implement the SPEC, not
any one client's quirks.

Add your port as a NEW top-level directory written idiomatically in
{{language}}. Do NOT modify the Python or TypeScript clients. Implement:

  - the inbetweenies-v2 sync client: canonical version strings, the
    server_time delta watermark used as an EXCLUSIVE `since`, the canonical
    conflict resolver (last-write-wins with a 1-second-window tiebreak on the
    greater version), and tombstone deletes;
  - a durable local graph cache of entities + relationships;
  - a stdio MCP server exposing the 12 tools named in the guide;
  - bearer-token auth on sync requests.

Conformance fixtures are in fixtures/ — version-strings.json,
knowledge-graph.json, sync-exchanges.json and mcp-tool-golden.json. Your port
must reproduce them exactly; they are the wire contract, not examples.

Constraints:
- Do NOT modify the existing Python or TypeScript clients, or the protocol spec.
- Your work must be additive: a new top-level directory plus its own tests.
