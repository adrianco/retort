-module(books_app).
-behaviour(application).

-export([start/2, stop/1]).

start(_StartType, _StartArgs) ->
    ok = books_db:init(),
    Dispatch = cowboy_router:compile([
        {'_', [
            {"/health", books_health_handler, []},
            {"/books", books_handler, []},
            {"/books/:id", books_handler, []}
        ]}
    ]),
    Port = application:get_env(books_app, port, 8080),
    {ok, _} = cowboy:start_clear(books_http_listener,
        [{port, Port}],
        #{env => #{dispatch => Dispatch}}),
    books_sup:start_link().

stop(_State) ->
    _ = cowboy:stop_listener(books_http_listener),
    books_db:close(),
    ok.
