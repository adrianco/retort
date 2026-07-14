-module(book_api_app).
-behaviour(application).

-export([start/2, stop/1]).

start(_Type, _Args) ->
    ok = book_store:init(),
    Dispatch = cowboy_router:compile([
        {'_', [
            {"/health", health_handler, []},
            {"/books", books_handler, []},
            {"/books/:id", book_handler, []}
        ]}
    ]),
    Port = application:get_env(book_api, port, 8080),
    {ok, _} = cowboy:start_clear(
        book_api_listener,
        [{port, Port}],
        #{env => #{dispatch => Dispatch}}
    ),
    book_api_sup:start_link().

stop(_State) ->
    _ = cowboy:stop_listener(book_api_listener),
    _ = book_store:close(),
    ok.
