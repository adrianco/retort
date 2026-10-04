-module(books_app).
-behaviour(application).

-export([start/2, stop/1, routes/0]).

start(_Type, _Args) ->
    Port = application:get_env(books, port, 8080),
    Dispatch = cowboy_router:compile(routes()),
    case books_sup:start_link() of
        {ok, Pid} ->
            {ok, _} = cowboy:start_clear(books_http, [{port, Port}],
                                         #{env => #{dispatch => Dispatch}}),
            {ok, Pid};
        Error ->
            Error
    end.

stop(_State) ->
    cowboy:stop_listener(books_http).

routes() ->
    [{'_', [
        {"/health", books_health_handler, []},
        {"/books", books_handler, collection},
        {"/books/:id", books_handler, item}
    ]}].
