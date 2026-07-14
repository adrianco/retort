-module(book_api).
-behaviour(application).

-export([start/2, stop/1]).

start(_Type, _Args) ->
    case whereis(book_db) of
        undefined -> ok;
        _ -> gen_server:stop(book_db)
    end,
    case ets:info(book_db) of
        undefined -> ok;
        _ -> ets:delete(book_db)
    end,
    {ok, Sup} = book_api_sup:start_link(),
    ok = book_db:start_link(),
    ok = start_http(),
    {ok, Sup}.

stop(_State) ->
    ok.

start_http() ->
    Dispatch = cowboy_router:compile([
        {'_', [
            {{"/health", [], book_api_handler, []}, []},
            {{"/books", [], book_api_handler, []}, []},
            {{"/books/:id", [], book_api_handler, []}, []}
        ]}
    ]),
    Env = #{dispatch => Dispatch},
    cowboy:start_clear(http_listener, [{port, 8080}], #{env => Env}).
