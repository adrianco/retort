-module(books_sup).
-behaviour(supervisor).

-export([start_link/0, init/1]).

start_link() ->
    supervisor:start_link({local, ?MODULE}, ?MODULE, []).

init([]) ->
    Children = [
        #{id => books_db,
          start => {books_db, start_link, []},
          restart => permanent,
          shutdown => 5000,
          type => worker,
          modules => [books_db]}
    ],
    {ok, {#{strategy => one_for_one, intensity => 5, period => 10}, Children}}.
