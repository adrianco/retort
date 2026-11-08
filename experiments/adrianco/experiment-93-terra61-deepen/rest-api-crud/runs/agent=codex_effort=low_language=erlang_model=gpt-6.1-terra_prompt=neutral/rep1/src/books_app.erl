-module(books_app).
-behaviour(application).
-export([start/2, stop/1]).

start(_Type, _Args) ->
    Dispatch = cowboy_router:compile([{'_', [
        {"/health", books_handler, health},
        {"/books", books_handler, collection},
        {"/books/:id", books_handler, item}
    ]}]),
    Port = application:get_env(books, port, 8080),
    case books_sup:start_link() of
        {ok, Sup} ->
            case cowboy:start_clear(books_http, [{port, Port}],
                    #{env => #{dispatch => Dispatch}}) of
                {ok, _} -> {ok, Sup};
                {error, Reason} -> exit(Sup, shutdown), {error, Reason}
            end;
        Error -> Error
    end.
stop(_State) -> cowboy:stop_listener(books_http), ok.
