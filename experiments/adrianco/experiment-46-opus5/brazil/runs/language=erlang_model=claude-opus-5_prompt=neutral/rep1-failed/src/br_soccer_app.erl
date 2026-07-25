%%%-------------------------------------------------------------------
%%% @doc Application callback: starts the supervision tree, which loads
%%% the data sets into the knowledge graph.
%%% @end
%%%-------------------------------------------------------------------
-module(br_soccer_app).

-behaviour(application).

-export([start/2, stop/1]).

start(_StartType, _StartArgs) ->
    br_soccer_sup:start_link().

stop(_State) ->
    ok.
