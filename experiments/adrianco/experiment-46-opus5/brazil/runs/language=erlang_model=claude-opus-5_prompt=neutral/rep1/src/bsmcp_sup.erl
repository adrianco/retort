%%%-------------------------------------------------------------------
%%% @doc Root supervisor. Only child is the dataset owner; it must be
%%% permanent because the ETS tables die with it.
%%% @end
%%%-------------------------------------------------------------------
-module(bsmcp_sup).
-behaviour(supervisor).

-export([start_link/0, init/1]).

start_link() ->
    supervisor:start_link({local, ?MODULE}, ?MODULE, []).

init([]) ->
    SupFlags = #{strategy => one_for_one, intensity => 3, period => 60},
    Children = [#{id => bsmcp_data,
                  start => {bsmcp_data, start_link, []},
                  restart => permanent,
                  shutdown => 5000,
                  type => worker,
                  modules => [bsmcp_data]}],
    {ok, {SupFlags, Children}}.
