%%%-------------------------------------------------------------------
%%% @doc Application callback: brings up the embedded database and the
%%% Cowboy HTTP listener.
%%% @end
%%%-------------------------------------------------------------------
-module(book_api_app).

-behaviour(application).

-export([start/2, stop/1]).
-export([port/0, routes/0]).

-define(LISTENER, book_api_http).

%%%===================================================================
%%% application callbacks
%%%===================================================================

start(_StartType, _StartArgs) ->
    ok = book_store:init(db_dir()),
    Port = configured_port(),
    Dispatch = cowboy_router:compile(routes()),
    case cowboy:start_clear(?LISTENER, [{port, Port}],
                            #{env => #{dispatch => Dispatch}}) of
        {ok, _Pid} ->
            logger:info("book_api listening on port ~b", [port()]),
            book_api_sup:start_link();
        {error, eaddrinuse} ->
            %% By far the most common startup failure; say so plainly instead
            %% of letting a badmatch surface as a supervisor report.
            {error, {port_in_use, Port,
                     "set BOOK_API_PORT to a free port and try again"}};
        {error, Reason} ->
            {error, {listener_failed, Reason}}
    end.

stop(_State) ->
    _ = cowboy:stop_listener(?LISTENER),
    ok.

%%%===================================================================
%%% API
%%%===================================================================

%% @doc The port the listener actually bound to. Differs from the
%% configured value when port 0 (ephemeral) was requested, which is how
%% the test suite avoids clashing with a running server.
-spec port() -> inet:port_number().
port() ->
    ranch:get_port(?LISTENER).

-spec routes() -> cowboy_router:routes().
routes() ->
    [{'_', [{"/health", book_api_health_h, []},
            {"/books", book_api_books_h, []},
            {"/books/:id", book_api_book_h, []},
            {'_', book_api_notfound_h, []}]}].

%%%===================================================================
%%% Configuration
%%%===================================================================

configured_port() ->
    from_env("BOOK_API_PORT", port,
             fun(Str) -> list_to_integer(string:trim(Str)) end).

db_dir() ->
    from_env("BOOK_API_DB_DIR", db_dir, fun(Str) -> Str end).

from_env(EnvVar, Key, Parse) ->
    case os:getenv(EnvVar) of
        false -> application:get_env(book_api, Key, default(Key));
        "" -> application:get_env(book_api, Key, default(Key));
        Value -> Parse(Value)
    end.

default(port) -> 8080;
default(db_dir) -> "data".
