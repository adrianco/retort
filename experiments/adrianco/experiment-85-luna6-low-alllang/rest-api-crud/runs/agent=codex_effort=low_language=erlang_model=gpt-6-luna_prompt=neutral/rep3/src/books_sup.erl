-module(books_sup).
-behaviour(supervisor).

-export([start_link/0, init/1]).

start_link() ->
    supervisor:start_link({local, ?MODULE}, ?MODULE, []).

init([]) ->
    Port = env_int(port, 8080),
    DbPath = application:get_env(books, db_path, "books.sqlite3"),
    Children = [#{id => books_store,
                  start => {books_store, start_link, [DbPath]},
                  restart => permanent,
                  shutdown => 5000,
                  type => worker,
                  modules => [books_store]},
                #{id => books_http,
                  start => {books_http, start_link, [Port]},
                  restart => permanent,
                  shutdown => 5000,
                  type => worker,
                  modules => [books_http]}],
    {ok, {{one_for_one, 5, 10}, Children}}.

env_int(Key, Default) ->
    case application:get_env(books, Key) of
        {ok, Value} when is_integer(Value) -> Value;
        _ -> Default
    end.
