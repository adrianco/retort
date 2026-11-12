-module(bookstore_app).
-behaviour(application).

-export([start/2, stop/1, port/0]).

-define(LISTENER, bookstore_http).

start(_Type, _Args) ->
    Port = env_int("PORT", application:get_env(bookstore, port, 8080)),
    Dispatch = cowboy_router:compile([
        {'_', [
            {"/health", bookstore_handler, health},
            {"/books", bookstore_handler, collection},
            {"/books/:id", bookstore_handler, item}
        ]}
    ]),
    case bookstore_sup:start_link() of
        {ok, Sup} ->
            {ok, _} = cowboy:start_clear(?LISTENER, [{port, Port}],
                                         #{env => #{dispatch => Dispatch}}),
            {ok, Sup};
        Error ->
            Error
    end.

stop(_State) ->
    cowboy:stop_listener(?LISTENER).

%% @doc The TCP port actually bound (useful when configured with port 0).
port() ->
    ranch:get_port(?LISTENER).

env_int(Name, Default) ->
    case os:getenv(Name) of
        false -> Default;
        Value ->
            try list_to_integer(Value) catch _:_ -> Default end
    end.
