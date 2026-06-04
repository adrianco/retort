%%%-------------------------------------------------------------------
%% @doc booksapp public API
%% Starts the Cowboy HTTP listener and the top-level supervisor.
%%%-------------------------------------------------------------------
-module(booksapp_app).
-behaviour(application).

-export([start/2, stop/1]).

start(_StartType, _StartArgs) ->
    Dispatch = cowboy_router:compile([
        {'_', [
            {"/health", health_handler, []},
            {"/books", books_handler, []},
            {"/books/:id", books_handler, []}
        ]}
    ]),
    Port = application:get_env(booksapp, port, 8080),
    {ok, _} = cowboy:start_clear(booksapp_http_listener,
        [{port, Port}],
        #{env => #{dispatch => Dispatch}}
    ),
    booksapp_sup:start_link().

stop(_State) ->
    ok = cowboy:stop_listener(booksapp_http_listener).
