%%%-------------------------------------------------------------------
%% @doc booksapp top level supervisor.
%%%-------------------------------------------------------------------
-module(booksapp_sup).
-behaviour(supervisor).

-export([start_link/0]).
-export([init/1]).

start_link() ->
    supervisor:start_link({local, ?MODULE}, ?MODULE, []).

init([]) ->
    SupFlags = #{
        strategy => one_for_one,
        intensity => 5,
        period => 10
    },
    ChildSpecs = [
        #{
            id => book_store,
            start => {book_store, start_link, []},
            restart => permanent,
            shutdown => 5000,
            type => worker,
            modules => [book_store]
        }
    ],
    {ok, {SupFlags, ChildSpecs}}.
