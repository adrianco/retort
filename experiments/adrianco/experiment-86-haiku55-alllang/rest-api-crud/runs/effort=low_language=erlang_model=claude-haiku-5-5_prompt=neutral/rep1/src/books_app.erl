-module(books_app).
-behaviour(application).

-export([start/2, stop/1]).
-export([port/0, db_path/0]).

-define(LISTENER, books_http).

start(_StartType, _StartArgs) ->
    {ok, Sup} = books_sup:start_link(db_path()),
    {ok, _} = cowboy:start_clear(?LISTENER, [{port, port()}], #{env => #{dispatch => dispatch()}}),
    {ok, Sup}.

stop(_State) ->
    _ = cowboy:stop_listener(?LISTENER),
    ok.

%% The HTTP port and database path can be overridden with the
%% BOOKS_PORT and BOOKS_DB_PATH environment variables.
port() ->
    case os:getenv("BOOKS_PORT") of
        false -> application:get_env(books, port, 8080);
        Value -> list_to_integer(Value)
    end.

db_path() ->
    case os:getenv("BOOKS_DB_PATH") of
        false -> application:get_env(books, db_path, "books.db");
        Value -> Value
    end.

dispatch() ->
    cowboy_router:compile([
        {'_', [
            {"/health", books_health_handler, []},
            {"/books", books_collection_handler, []},
            {"/books/:id", books_item_handler, []}
        ]}
    ]).
