%% @doc escript entry point for the Brazilian Soccer MCP server.
-module(bsmcp).

-export([main/1]).

main(Args) ->
    bsmcp_server:main(Args).
