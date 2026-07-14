-module(br_soccer_mcp_app).
-behaviour(application).
-export([start/2, stop/1]).

start(_StartType, _StartArgs) ->
    br_soccer_mcp_sup:start_link().

stop(_State) ->
    ok.
