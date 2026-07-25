%%%-------------------------------------------------------------------
%%% @doc Root supervisor.  The store is the only long lived process:
%%% it owns the ETS tables and the knowledge graph.
%%% @end
%%%-------------------------------------------------------------------
-module(br_soccer_sup).

-behaviour(supervisor).

-export([start_link/0, init/1]).

start_link() ->
    supervisor:start_link({local, ?MODULE}, ?MODULE, []).

init([]) ->
    SupFlags = #{strategy => one_for_one, intensity => 3, period => 60},
    Children =
        [#{id => br_store,
           start => {br_store, start_link, []},
           restart => permanent,
           shutdown => 10000,
           type => worker,
           modules => [br_store]}],
    {ok, {SupFlags, Children}}.
