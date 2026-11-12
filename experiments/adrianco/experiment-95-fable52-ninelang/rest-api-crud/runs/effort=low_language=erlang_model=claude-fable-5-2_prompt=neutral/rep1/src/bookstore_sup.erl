-module(bookstore_sup).
-behaviour(supervisor).

-export([start_link/0, init/1]).

start_link() ->
    supervisor:start_link({local, ?MODULE}, ?MODULE, []).

init([]) ->
    Path = case os:getenv("DB_PATH") of
        false -> application:get_env(bookstore, db_path, "books.db");
        P -> P
    end,
    Db = #{id => bookstore_db,
           start => {bookstore_db, start_link, [Path]},
           restart => permanent,
           type => worker},
    {ok, {#{strategy => one_for_one, intensity => 5, period => 10}, [Db]}}.
