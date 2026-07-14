-module(bookapi_server).

-export([start_link/0]).

start_link() ->
    Port = application:get_env(bookapi, port, 8080),
    Dispatch = dispatch(),
    {ok, _} = cowboy:start_clear(http,
        [{port, Port}],
        #{env => #{dispatch => Dispatch}}),
    loop().

dispatch() ->
    cowboy_router:compile([
        {'_', [
            {"/health", bookapi_health_handler, []},
            {"/books", bookapi_collection_handler, []},
            {"/books/:id", bookapi_item_handler, []}
        ]}
    ]).

loop() ->
    receive
        stop -> ok
    end.
