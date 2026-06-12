-module(brazilian_soccer_mcp).
-export([main/1]).

main(_Args) ->
    application:ensure_all_started(thoas),
    bsm_mcp_server:start().
