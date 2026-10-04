-module(books_app).
-behaviour(application).

-export([start/2, stop/1]).

-define(LISTENER, books_http).

start(_Type, _Args) ->
    case books_sup:start_link() of
        {ok, Pid} ->
            Dispatch = cowboy_router:compile([
                {'_', [
                    {"/health", books_handler, health},
                    {"/books", books_handler, collection},
                    {"/books/:id", books_handler, item}
                ]}
            ]),
            {ok, _} = cowboy:start_clear(
                ?LISTENER,
                [{port, port()}],
                #{env => #{dispatch => Dispatch}}
            ),
            {ok, Pid};
        Error ->
            Error
    end.

stop(_State) ->
    cowboy:stop_listener(?LISTENER).

%% The PORT environment variable overrides the application env.
port() ->
    case os:getenv("PORT") of
        false ->
            application:get_env(books, port, 8080);
        Str ->
            list_to_integer(Str)
    end.
