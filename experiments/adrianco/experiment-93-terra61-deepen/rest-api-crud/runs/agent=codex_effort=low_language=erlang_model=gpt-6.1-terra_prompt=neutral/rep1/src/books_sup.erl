-module(books_sup).
-behaviour(supervisor).
-export([start_link/0, init/1]).
start_link() -> supervisor:start_link({local, ?MODULE}, ?MODULE, []).
init([]) ->
    Child = #{id => books_store, start => {books_store, start_link, []},
              restart => permanent, type => worker},
    {ok, {#{strategy => one_for_one, intensity => 5, period => 10}, [Child]}}.
