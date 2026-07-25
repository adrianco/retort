%% Application callback: starts the supervisor and the HTTP listener.
-module(books_app).
-behaviour(application).

-export([start/2, stop/1]).

start(_StartType, _StartArgs) ->
    {ok, Pid} = books_sup:start_link(),
    Port = application:get_env(books, port, 8080),
    Dispatch = cowboy_router:compile([
        {'_', [
            {"/health", health_handler, []},
            {"/books", books_handler, []},
            {"/books/:id", books_handler, []}
        ]}
    ]),
    {ok, _} = cowboy:start_clear(books_http_listener,
                                 [{port, Port}],
                                 #{env => #{dispatch => Dispatch}}),
    {ok, Pid}.

stop(_State) ->
    ok = cowboy:stop_listener(books_http_listener),
    ok.
