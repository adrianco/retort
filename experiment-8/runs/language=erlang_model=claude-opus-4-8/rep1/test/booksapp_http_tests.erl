%%%-------------------------------------------------------------------
%% @doc Integration tests driving the running HTTP API over httpc.
%%%-------------------------------------------------------------------
-module(booksapp_http_tests).
-include_lib("eunit/include/eunit.hrl").

-define(BASE, "http://localhost:8090").

setup() ->
    %% Load before setting env so the {env,...} defaults in the .app
    %% file don't overwrite our test port during application:load/1.
    ok = ensure_loaded(booksapp),
    application:set_env(booksapp, port, 8090),
    {ok, _} = application:ensure_all_started(booksapp),
    {ok, _} = application:ensure_all_started(inets),
    book_store:clear(),
    ok.

ensure_loaded(App) ->
    case application:load(App) of
        ok -> ok;
        {error, {already_loaded, App}} -> ok
    end.

cleanup(_) ->
    application:stop(booksapp),
    ok.

http_test_() ->
    {setup, fun setup/0, fun cleanup/1,
     [
        fun health_endpoint/0,
        fun create_and_fetch_book/0,
        fun create_validation_error/0,
        fun list_with_author_filter/0,
        fun update_and_delete/0,
        fun missing_book_is_404/0
     ]}.

health_endpoint() ->
    {Code, Body} = request(get, "/health"),
    ?assertEqual(200, Code),
    ?assertEqual(<<"ok">>, maps:get(<<"status">>, Body)).

create_and_fetch_book() ->
    {Code, Book} = request(post, "/books", #{
        <<"title">> => <<"Designing for Scale">>,
        <<"author">> => <<"A. Cockcroft">>,
        <<"year">> => 2020
    }),
    ?assertEqual(201, Code),
    Id = maps:get(<<"id">>, Book),
    {GetCode, Fetched} = request(get, "/books/" ++ integer_to_list(Id)),
    ?assertEqual(200, GetCode),
    ?assertEqual(<<"Designing for Scale">>, maps:get(<<"title">>, Fetched)).

create_validation_error() ->
    {Code, Body} = request(post, "/books", #{<<"author">> => <<"No Title">>}),
    ?assertEqual(400, Code),
    ?assert(maps:is_key(<<"error">>, Body)).

list_with_author_filter() ->
    {201, _} = request(post, "/books", #{<<"title">> => <<"X">>,
                                         <<"author">> => <<"Filter Me">>}),
    {Code, List} = request(get, "/books?author=Filter%20Me"),
    ?assertEqual(200, Code),
    ?assert(is_list(List)),
    ?assert(lists:all(fun(B) ->
        maps:get(<<"author">>, B) =:= <<"Filter Me">>
    end, List)),
    ?assert(length(List) >= 1).

update_and_delete() ->
    {201, Book} = request(post, "/books", #{<<"title">> => <<"Temp">>,
                                            <<"author">> => <<"Auth">>}),
    Id = maps:get(<<"id">>, Book),
    Path = "/books/" ++ integer_to_list(Id),
    {UCode, Updated} = request(put, Path, #{<<"title">> => <<"Renamed">>}),
    ?assertEqual(200, UCode),
    ?assertEqual(<<"Renamed">>, maps:get(<<"title">>, Updated)),
    {DCode, _} = request(delete, Path),
    ?assertEqual(204, DCode),
    {GCode, _} = request(get, Path),
    ?assertEqual(404, GCode).

missing_book_is_404() ->
    {Code, _} = request(get, "/books/123456"),
    ?assertEqual(404, Code).

%%====================================================================
%% HTTP helpers
%%====================================================================

request(Method, Path) ->
    do_request(Method, Path, undefined).

request(Method, Path, BodyMap) ->
    do_request(Method, Path, BodyMap).

do_request(Method, Path, BodyMap) ->
    Url = ?BASE ++ Path,
    Request =
        case BodyMap of
            undefined -> {Url, []};
            _ -> {Url, [], "application/json", json:encode(BodyMap)}
        end,
    {ok, {{_, Status, _}, _Headers, Body}} =
        httpc:request(Method, Request, [], []),
    {Status, decode_body(Body)}.

decode_body([]) -> #{};
decode_body(Body) ->
    Bin = iolist_to_binary(Body),
    case Bin of
        <<>> -> #{};
        _ -> json:decode(Bin)
    end.
