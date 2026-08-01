-module(books_sup).
-behaviour(supervisor).

-export([start_link/0, init/1]).

start_link() -> supervisor:start_link({local, ?MODULE}, ?MODULE, []).

init([]) ->
    File = application:get_env(books_api, storage_file, "books.dets"),
    Port = application:get_env(books_api, port, 8080),
    {ok, {{one_for_one, 5, 10}, [
        #{id => books_store, start => {books_store, start_link, [File]},
          restart => permanent, shutdown => 5000, type => worker, modules => [books_store]},
        #{id => books_http, start => {books_http, start_link, [Port]},
          restart => permanent, shutdown => 5000, type => worker, modules => [books_http]}
    ]}}.
