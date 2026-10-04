-module(book_api_app).
-behaviour(application).

-export([start/2, stop/1, port/0]).

-define(LISTENER, book_api_http).

start(_Type, _Args) ->
    case book_api_sup:start_link() of
        {ok, Pid} ->
            Dispatch = cowboy_router:compile([
                {'_', [
                    {"/health", book_api_health_handler, []},
                    {"/books", book_api_books_handler, collection},
                    {"/books/:id", book_api_books_handler, item}
                ]}
            ]),
            {ok, _} = cowboy:start_clear(
                ?LISTENER,
                [{port, configured_port()}],
                #{env => #{dispatch => Dispatch}}
            ),
            {ok, Pid};
        Error ->
            Error
    end.

stop(_State) ->
    cowboy:stop_listener(?LISTENER).

%% Port the HTTP listener is actually bound to (useful when configured as 0).
port() ->
    ranch:get_port(?LISTENER).

%% The PORT environment variable overrides the application env.
configured_port() ->
    case os:getenv("PORT") of
        false ->
            application:get_env(book_api, port, 8080);
        Str ->
            list_to_integer(Str)
    end.
