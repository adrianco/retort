%%%-------------------------------------------------------------------
%%% @doc Application callback. Starting the application loads the CSV
%%% datasets into ETS (see {@link bsmcp_data}); everything else in the
%%% system is stateless.
%%% @end
%%%-------------------------------------------------------------------
-module(bsmcp_app).
-behaviour(application).

-export([start/2, stop/1]).

start(_Type, _Args) ->
    bsmcp_sup:start_link().

stop(_State) ->
    ok.
