%% Public executable entry point for the Brazilian Soccer MCP server.
%%
%% Keeping this small wrapper separate from the protocol implementation makes
%% the command advertised in the README stable: `erl ... -s
%% brazilian_soccer_mcp main`.
-module(brazilian_soccer_mcp).

-export([main/0, run/0, handle/2, tools/0]).

main() -> soccer_mcp:main().
run() -> main().
handle(Request, Data) -> soccer_mcp:handle(Request, Data).
tools() -> soccer_mcp:tools().
