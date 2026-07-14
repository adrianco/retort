%%% @doc Integration tests exercising the running HTTP API end-to-end.
-module(book_api_SUITE).

-include_lib("common_test/include/ct.hrl").
-include_lib("stdlib/include/assert.hrl").

-export([all/0, init_per_suite/1, end_per_suite/1, init_per_testcase/2]).
-export([
    health_check/1,
    create_book/1,
    create_requires_title_and_author/1,
    create_rejects_invalid_json/1,
    list_books/1,
    list_filter_by_author/1,
    get_book/1,
    get_missing_book_returns_404/1,
    update_book/1,
    delete_book/1
]).

all() ->
    [
        health_check,
        create_book,
        create_requires_title_and_author,
        create_rejects_invalid_json,
        list_books,
        list_filter_by_author,
        get_book,
        get_missing_book_returns_404,
        update_book,
        delete_book
    ].

init_per_suite(Config) ->
    {ok, _} = application:ensure_all_started(book_api),
    {ok, _} = application:ensure_all_started(inets),
    Port = application:get_env(book_api, port, 8080),
    [{base_url, "http://localhost:" ++ integer_to_list(Port)} | Config].

end_per_suite(_Config) ->
    application:stop(book_api),
    ok.

init_per_testcase(_Case, Config) ->
    %% Start each test from an empty collection.
    {atomic, ok} = mnesia:clear_table(book),
    Config.

%%% --- Tests ---

health_check(Config) ->
    {Status, Body} = req(get, Config, "/health"),
    ?assertEqual(200, Status),
    ?assertEqual(<<"ok">>, maps:get(<<"status">>, Body)).

create_book(Config) ->
    Payload = #{title => <<"Dune">>, author => <<"Frank Herbert">>,
                year => 1965, isbn => <<"9780441013593">>},
    {Status, Body} = req(post, Config, "/books", Payload),
    ?assertEqual(201, Status),
    ?assertEqual(<<"Dune">>, maps:get(<<"title">>, Body)),
    ?assertEqual(<<"Frank Herbert">>, maps:get(<<"author">>, Body)),
    ?assertEqual(1965, maps:get(<<"year">>, Body)),
    ?assert(is_integer(maps:get(<<"id">>, Body))).

create_requires_title_and_author(Config) ->
    {Status1, Body1} = req(post, Config, "/books", #{author => <<"Nobody">>}),
    ?assertEqual(400, Status1),
    ?assert(maps:is_key(<<"error">>, Body1)),

    {Status2, _} = req(post, Config, "/books", #{title => <<"No Author">>}),
    ?assertEqual(400, Status2),

    {Status3, _} = req(post, Config, "/books",
                       #{title => <<"">>, author => <<"X">>}),
    ?assertEqual(400, Status3).

create_rejects_invalid_json(Config) ->
    {Status, _} = raw_req(post, Config, "/books", <<"{not valid json">>),
    ?assertEqual(400, Status).

list_books(Config) ->
    _ = req(post, Config, "/books", #{title => <<"A">>, author => <<"X">>}),
    _ = req(post, Config, "/books", #{title => <<"B">>, author => <<"Y">>}),
    {Status, Body} = req(get, Config, "/books"),
    ?assertEqual(200, Status),
    ?assert(is_list(Body)),
    ?assertEqual(2, length(Body)).

list_filter_by_author(Config) ->
    _ = req(post, Config, "/books", #{title => <<"A">>, author => <<"Tolkien">>}),
    _ = req(post, Config, "/books", #{title => <<"B">>, author => <<"Tolkien">>}),
    _ = req(post, Config, "/books", #{title => <<"C">>, author => <<"Asimov">>}),
    {Status, Body} = req(get, Config, "/books?author=Tolkien"),
    ?assertEqual(200, Status),
    ?assertEqual(2, length(Body)),
    ?assert(lists:all(fun(B) -> maps:get(<<"author">>, B) =:= <<"Tolkien">> end, Body)).

get_book(Config) ->
    {_, Created} = req(post, Config, "/books",
                       #{title => <<"1984">>, author => <<"Orwell">>}),
    Id = maps:get(<<"id">>, Created),
    {Status, Body} = req(get, Config, "/books/" ++ integer_to_list(Id)),
    ?assertEqual(200, Status),
    ?assertEqual(<<"1984">>, maps:get(<<"title">>, Body)).

get_missing_book_returns_404(Config) ->
    {Status, _} = req(get, Config, "/books/999999"),
    ?assertEqual(404, Status).

update_book(Config) ->
    {_, Created} = req(post, Config, "/books",
                       #{title => <<"Old">>, author => <<"Author">>}),
    Id = maps:get(<<"id">>, Created),
    {Status, Body} = req(put, Config, "/books/" ++ integer_to_list(Id),
                         #{title => <<"New Title">>, year => 2020}),
    ?assertEqual(200, Status),
    ?assertEqual(<<"New Title">>, maps:get(<<"title">>, Body)),
    ?assertEqual(<<"Author">>, maps:get(<<"author">>, Body)),
    ?assertEqual(2020, maps:get(<<"year">>, Body)),

    {MissingStatus, _} = req(put, Config, "/books/999999", #{title => <<"X">>}),
    ?assertEqual(404, MissingStatus).

delete_book(Config) ->
    {_, Created} = req(post, Config, "/books",
                       #{title => <<"Temp">>, author => <<"Author">>}),
    Id = maps:get(<<"id">>, Created),
    Path = "/books/" ++ integer_to_list(Id),
    {Status, _} = req(delete, Config, Path),
    ?assertEqual(204, Status),
    {GetStatus, _} = req(get, Config, Path),
    ?assertEqual(404, GetStatus),
    {DelMissing, _} = req(delete, Config, "/books/999999"),
    ?assertEqual(404, DelMissing).

%%% --- HTTP client helpers ---

req(Method, Config, Path) ->
    raw_req(Method, Config, Path, undefined).

req(Method, Config, Path, Payload) ->
    raw_req(Method, Config, Path, json:encode(Payload)).

raw_req(Method, Config, Path, Body) ->
    Url = ?config(base_url, Config) ++ Path,
    Request = case Body of
        undefined -> {Url, []};
        _ -> {Url, [], "application/json", Body}
    end,
    {ok, {{_, Status, _}, _Headers, RespBody}} =
        httpc:request(Method, Request, [], [{body_format, binary}]),
    {Status, decode(RespBody)}.

decode(<<>>) -> <<>>;
decode(Body) ->
    try json:decode(Body)
    catch _:_ -> Body
    end.
