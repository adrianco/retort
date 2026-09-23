-module(books_app).
-behaviour(application).
-behaviour(supervisor).
-export([start/2, stop/1, init/1]).

start(_Type, _Args) ->
    supervisor:start_link({local, books_sup}, ?MODULE, []).

stop(_State) -> ok.

init([]) ->
    {ok, Port} = application:get_env(books, port),
    {ok, File} = application:get_env(books, db_file),
    Children = [#{id => books_db, start => {books_db, start_link, [File]}},
                #{id => books_http, start => {books_http, start_link, [Port]}}],
    {ok, {#{strategy => one_for_all, intensity => 5, period => 10}, Children}}.
