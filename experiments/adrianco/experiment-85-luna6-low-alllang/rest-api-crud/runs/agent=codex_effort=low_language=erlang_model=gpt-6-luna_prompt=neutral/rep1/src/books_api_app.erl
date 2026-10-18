-module(books_api_app).
-behaviour(application).
-export([start/2, stop/1]).
start(_Type, _Args) ->
    {ok, _} = books_api_store:start_link(),
    Dispatch = cowboy_router:compile([{'_', [{"/health", books_api_handler, []}, {"/books", books_api_handler, []}, {"/books/:id", books_api_handler, []}]}]),
    Port = application:get_env(books_api, port, 8080),
    cowboy:start_clear(books_http_listener, [{port, Port}], #{env => #{dispatch => Dispatch}}).
stop(_State) -> ok.
