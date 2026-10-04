-module(books_sup).
-behaviour(supervisor).

-export([start_link/0, init/1]).

start_link() ->
    supervisor:start_link({local, ?MODULE}, ?MODULE, []).

init([]) ->
    Path = application:get_env(books, db_path, "books.db"),
    Child = #{id => books_db,
              start => {books_db, start_link, [Path]},
              restart => permanent,
              shutdown => 5000,
              type => worker},
    {ok, {#{strategy => one_for_one, intensity => 5, period => 10}, [Child]}}.
