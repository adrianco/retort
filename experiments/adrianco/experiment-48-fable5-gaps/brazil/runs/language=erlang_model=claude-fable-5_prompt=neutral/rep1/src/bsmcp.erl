%% Escript entry point: `rebar3 escriptize` builds _build/default/bin/bsmcp,
%% which speaks MCP over stdio. Optional first argument = data directory
%% (default: data/kaggle, overridable with BSMCP_DATA_DIR).
-module(bsmcp).

-export([main/1]).

main(Args) ->
    bsmcp_server:main(Args).
