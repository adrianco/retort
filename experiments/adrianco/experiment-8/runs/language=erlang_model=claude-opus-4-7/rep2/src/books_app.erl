-module(books_app).
-behaviour(application).

-export([start/2, stop/1]).

start(_StartType, _StartArgs) ->
    {ok, SupPid} = books_sup:start_link(),
    Dispatch = cowboy_router:compile([
        {'_', [
            {"/health", health_handler, []},
            {"/books", books_handler, []},
            {"/books/:id", books_handler, []}
        ]}
    ]),
    Port = application:get_env(books, port, 8080),
    {ok, _} = cowboy:start_clear(books_listener,
        [{port, Port}],
        #{env => #{dispatch => Dispatch}}),
    {ok, SupPid}.

stop(_State) ->
    _ = cowboy:stop_listener(books_listener),
    ok.
