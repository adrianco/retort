-module(books_api_app).
-behaviour(application).
-export([start/2, stop/1]).

start(_Type, _Args) ->
    {ok, Pid} = books_api_sup:start_link(),
    Dispatch = cowboy_router:compile([{'_', [{"/health", books_http_handler, health},
        {"/books", books_http_handler, books}, {"/books/:id", books_http_handler, book}]}]),
    Port = application:get_env(books_api, port, 8080),
    {ok, _} = cowboy:start_clear(books_http_listener, [{port, Port}], #{env => #{dispatch => Dispatch}}),
    {ok, Pid}.

stop(_State) -> cowboy:stop_listener(books_http_listener), ok.
