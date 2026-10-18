-module(books_app).
-behaviour(application).

-export([start/2, stop/1]).

start(_Type, _Args) ->
    Port = application:get_env(books, port, 8080),
    DbFile = application:get_env(books, db_file, "books.dets"),
    Dispatch = cowboy_router:compile([
        {'_', [
            {"/health", books_http, health},
            {"/books", books_http, collection},
            {"/books/:id", books_http, item}
        ]}
    ]),
    case books_sup:start_link(DbFile) of
        {ok, Sup} ->
            {ok, _} = cowboy:start_clear(books_http, [{port, Port}],
                                         #{env => #{dispatch => Dispatch}}),
            {ok, Sup};
        Error ->
            Error
    end.

stop(_State) ->
    _ = cowboy:stop_listener(books_http),
    ok.
