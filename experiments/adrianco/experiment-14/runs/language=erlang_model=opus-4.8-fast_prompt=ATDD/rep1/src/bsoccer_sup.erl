%%% ===================================================================
%%% Brazilian Soccer MCP Server - top level supervisor
%%%
%%% Context: Supervises `bsoccer_data', the single worker that owns the
%%% in-memory (ETS) Brazilian soccer corpus and serves all queries used
%%% by the MCP tool layer. A one_for_one strategy is sufficient because
%%% there is a single, self-contained worker; if data loading crashes we
%%% want it restarted so the server can recover.
%%% ===================================================================
-module(bsoccer_sup).
-behaviour(supervisor).

-export([start_link/1, init/1]).

start_link(DataDir) ->
    supervisor:start_link({local, ?MODULE}, ?MODULE, DataDir).

init(DataDir) ->
    SupFlags = #{strategy => one_for_one,
                 intensity => 1,
                 period => 5},
    ChildSpecs = [#{id => bsoccer_data,
                    start => {bsoccer_data, start_link, [DataDir]},
                    restart => permanent,
                    shutdown => 5000,
                    type => worker,
                    modules => [bsoccer_data]}],
    {ok, {SupFlags, ChildSpecs}}.
