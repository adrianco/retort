-module(books_api_sup).
-behaviour(supervisor).
-export([start_link/0, init/1]).
start_link() -> supervisor:start_link({local, ?MODULE}, ?MODULE, []).
init([]) ->
    Path = application:get_env(books_api, db_path, "books.db"),
    Child = #{id => books_db, start => {books_db, start_link, [Path]}, restart => permanent,
              shutdown => 5000, type => worker, modules => [books_db]},
    {ok, {{one_for_one, 5, 10}, [Child]}}.
