%%%-------------------------------------------------------------------
%% @doc brazilian_soccer_mcp public API
%% @end
%%%-------------------------------------------------------------------

-module(brazilian_soccer_mcp_app).

-behaviour(application).

-export([start/2, stop/1]).

start(_StartType, _StartArgs) ->
    {ok, Pid} = brazilian_soccer_mcp_sup:start_link(),
    ok = bsm_data:load_all(),
    {ok, Pid}.

stop(_State) ->
    ok.
