-module(book_api_sup).
-behaviour(supervisor).

-export([start_link/0, init/1]).

start_link() ->
    supervisor:start_link({local, ?MODULE}, ?MODULE, []).

init([]) ->
    DbFile =
        case os:getenv("BOOKS_DB") of
            false -> application:get_env(book_api, db_file, "books.dets");
            Path -> Path
        end,
    Store = #{
        id => book_store,
        start => {book_store, start_link, [DbFile]}
    },
    {ok, {#{strategy => one_for_one, intensity => 5, period => 10}, [Store]}}.
