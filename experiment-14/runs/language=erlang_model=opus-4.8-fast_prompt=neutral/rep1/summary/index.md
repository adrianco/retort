# Summary: language=erlang_model=opus-4.8-fast_prompt=neutral · rep 1

- **Shape:** Plain-Erlang/OTP MCP server — gen_server CSV loader → two protected ETS tables → query layer → JSON-RPC 2.0 stdio transport, packaged as a rebar3 escript. No third-party deps (OTP 27+ built-in `json`).
- **Structure:** 6 source modules (+ `.app.src`) / 1 EUnit test module (~24 cases).
- **Interfaces:** 7 MCP tools, 5 JSON-RPC methods, 3 CLI invocations; 2 in-memory ETS schemas (~22k matches, ~18k players).
- **Notable:** Thoughtful data layer — cross-file `{competition, season}` source-priority dedup and dual fuzzy/precise team-name keys (so the 2019 Brasileirão table correctly crowns Flamengo at 90 pts and state-suffixed clubs aren't merged). Among the more complete approaches: every capability has a tool and a backing integration test.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
