-module(books_api_tests).
-include_lib("eunit/include/eunit.hrl").

-define(PORT, 8765).
-define(BASE, "http://127.0.0.1:8765").
-define(TEST_FILE, "books_api_test.dets").

setup() ->
    file:delete(?TEST_FILE),
    application:load(books_app),
    application:set_env(books_app, port, ?PORT),
    application:set_env(books_app, db_file, ?TEST_FILE),
    {ok, _} = application:ensure_all_started(books_app),
    {ok, _} = application:ensure_all_started(inets),
    ok.

teardown(_) ->
    application:stop(books_app),
    application:stop(inets),
    file:delete(?TEST_FILE),
    ok.

api_test_() ->
    {setup, fun setup/0, fun teardown/1, [
        fun health_endpoint/0,
        fun create_and_get/0,
        fun create_missing_title_returns_400/0,
        fun list_and_filter/0,
        fun update_book/0,
        fun delete_book/0,
        fun get_missing_returns_404/0
    ]}.

%% Helpers

request(Method, Path) ->
    request(Method, Path, undefined).

request(Method, Path, Body) ->
    URL = ?BASE ++ Path,
    Req = case Body of
        undefined when Method =:= get; Method =:= delete ->
            {URL, []};
        undefined ->
            {URL, [], "application/json", <<>>};
        _ ->
            {URL, [], "application/json", jsone:encode(Body)}
    end,
    {ok, {{_, Status, _}, _Headers, RespBody}} =
        httpc:request(Method, Req, [], [{body_format, binary}]),
    DecodedBody = case RespBody of
        <<>> -> undefined;
        _ ->
            try jsone:decode(RespBody, [{object_format, map}])
            catch _:_ -> RespBody
            end
    end,
    {Status, DecodedBody}.

%% Tests

health_endpoint() ->
    {Status, Body} = request(get, "/health"),
    ?assertEqual(200, Status),
    ?assertEqual(<<"ok">>, maps:get(<<"status">>, Body)).

create_and_get() ->
    {Status, Book} = request(post, "/books", #{
        <<"title">> => <<"Learn You Some Erlang">>,
        <<"author">> => <<"Fred Hebert">>,
        <<"year">> => 2013,
        <<"isbn">> => <<"978-1-59327-435-1">>
    }),
    ?assertEqual(201, Status),
    Id = maps:get(<<"id">>, Book),
    ?assert(is_binary(Id)),
    {GetStatus, GetBook} = request(get, "/books/" ++ binary_to_list(Id)),
    ?assertEqual(200, GetStatus),
    ?assertEqual(<<"Learn You Some Erlang">>, maps:get(<<"title">>, GetBook)).

create_missing_title_returns_400() ->
    {Status, Body} = request(post, "/books", #{<<"author">> => <<"Anon">>}),
    ?assertEqual(400, Status),
    ?assert(maps:is_key(<<"error">>, Body)).

list_and_filter() ->
    {201, _} = request(post, "/books", #{
        <<"title">> => <<"Book A">>, <<"author">> => <<"Alice">>
    }),
    {201, _} = request(post, "/books", #{
        <<"title">> => <<"Book B">>, <<"author">> => <<"Bob">>
    }),
    {200, AllBooks} = request(get, "/books"),
    ?assert(is_list(AllBooks)),
    ?assert(length(AllBooks) >= 2),
    {200, AlicesBooks} = request(get, "/books?author=Alice"),
    ?assert(lists:all(fun(B) ->
        maps:get(<<"author">>, B) =:= <<"Alice">>
    end, AlicesBooks)),
    ?assert(length(AlicesBooks) >= 1).

update_book() ->
    {201, Created} = request(post, "/books", #{
        <<"title">> => <<"Original">>, <<"author">> => <<"Author">>
    }),
    Id = binary_to_list(maps:get(<<"id">>, Created)),
    {200, Updated} = request(put, "/books/" ++ Id, #{
        <<"title">> => <<"Revised">>
    }),
    ?assertEqual(<<"Revised">>, maps:get(<<"title">>, Updated)),
    ?assertEqual(<<"Author">>, maps:get(<<"author">>, Updated)).

delete_book() ->
    {201, Created} = request(post, "/books", #{
        <<"title">> => <<"Doomed">>, <<"author">> => <<"X">>
    }),
    Id = binary_to_list(maps:get(<<"id">>, Created)),
    {204, _} = request(delete, "/books/" ++ Id),
    {404, _} = request(get, "/books/" ++ Id).

get_missing_returns_404() ->
    {Status, Body} = request(get, "/books/nonexistent"),
    ?assertEqual(404, Status),
    ?assert(maps:is_key(<<"error">>, Body)).
