-module(books_sup).
-behaviour(supervisor).

-export([start_link/0, init/1]).

start_link() ->
    supervisor:start_link({local, ?MODULE}, ?MODULE, []).

init([]) ->
    Db = #{
        id => books_db,
        start => {books_db, start_link, []},
        restart => permanent,
        type => worker
    },
    {ok, {#{strategy => one_for_one, intensity => 5, period => 10}, [Db]}}.
