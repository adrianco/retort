-module(books_SUITE).

-include_lib("common_test/include/ct.hrl").

-export([all/0, init_per_suite/1, end_per_suite/1,
         init_per_testcase/2, end_per_testcase/2]).
-export([
    test_health/1,
    test_create_book/1,
    test_create_missing_title/1,
    test_create_missing_author/1,
    test_create_invalid_json/1,
    test_list_books/1,
    test_list_books_filter_by_author/1,
    test_get_book/1,
    test_get_not_found/1,
    test_update_book/1,
    test_update_not_found/1,
    test_delete_book/1,
    test_delete_not_found/1
]).

all() ->
    [test_health,
     test_create_book,
     test_create_missing_title,
     test_create_missing_author,
     test_create_invalid_json,
     test_list_books,
     test_list_books_filter_by_author,
     test_get_book,
     test_get_not_found,
     test_update_book,
     test_update_not_found,
     test_delete_book,
     test_delete_not_found].

init_per_suite(Config) ->
    PrivDir = ?config(priv_dir, Config),
    DbFile = filename:join(PrivDir, "test_books.dets"),
    case application:load(books) of
        ok -> ok;
        {error, {already_loaded, _}} -> ok
    end,
    application:set_env(books, db_file, DbFile),
    application:set_env(books, port, 18080),
    {ok, _} = application:ensure_all_started(books),
    {ok, _} = application:ensure_all_started(inets),
    [{base_url, "http://localhost:18080"} | Config].

end_per_suite(_Config) ->
    _ = application:stop(books),
    ok.

init_per_testcase(_TC, Config) ->
    ok = books_db:clear(),
    Config.

end_per_testcase(_TC, _Config) ->
    ok.

%% ---- helpers ----

base_url(Config) ->
    ?config(base_url, Config).

get_req(Url) ->
    httpc:request(get, {Url, []}, [], []).

post_req(Url, Body) ->
    httpc:request(post,
        {Url, [], "application/json", Body}, [], []).

put_req(Url, Body) ->
    httpc:request(put,
        {Url, [], "application/json", Body}, [], []).

delete_req(Url) ->
    httpc:request(delete, {Url, []}, [], []).

decode_body(Body) ->
    json:decode(iolist_to_binary(Body)).

encode_body(Term) ->
    iolist_to_binary(json:encode(Term)).

create_book(Config, Data) ->
    Url = base_url(Config) ++ "/books",
    {ok, {{_, 201, _}, _, RespBody}} = post_req(Url, encode_body(Data)),
    decode_body(RespBody).

%% ---- tests ----

test_health(Config) ->
    Url = base_url(Config) ++ "/health",
    {ok, {{_, 200, _}, _, Body}} = get_req(Url),
    Json = decode_body(Body),
    <<"ok">> = maps:get(<<"status">>, Json).

test_create_book(Config) ->
    Url = base_url(Config) ++ "/books",
    Body = encode_body(#{title => <<"The Hobbit">>,
                         author => <<"Tolkien">>,
                         year => 1937,
                         isbn => <<"9780547928227">>}),
    {ok, {{_, 201, _}, _, RespBody}} = post_req(Url, Body),
    Json = decode_body(RespBody),
    <<"The Hobbit">> = maps:get(<<"title">>, Json),
    <<"Tolkien">> = maps:get(<<"author">>, Json),
    1937 = maps:get(<<"year">>, Json),
    <<"9780547928227">> = maps:get(<<"isbn">>, Json),
    Id = maps:get(<<"id">>, Json),
    true = is_binary(Id).

test_create_missing_title(Config) ->
    Url = base_url(Config) ++ "/books",
    Body = encode_body(#{author => <<"Tolkien">>}),
    {ok, {{_, 400, _}, _, RespBody}} = post_req(Url, Body),
    Json = decode_body(RespBody),
    <<"title is required">> = maps:get(<<"error">>, Json).

test_create_missing_author(Config) ->
    Url = base_url(Config) ++ "/books",
    Body = encode_body(#{title => <<"Something">>}),
    {ok, {{_, 400, _}, _, RespBody}} = post_req(Url, Body),
    Json = decode_body(RespBody),
    <<"author is required">> = maps:get(<<"error">>, Json).

test_create_invalid_json(Config) ->
    Url = base_url(Config) ++ "/books",
    {ok, {{_, 400, _}, _, _}} = post_req(Url, <<"not-json">>).

test_list_books(Config) ->
    _ = create_book(Config, #{title => <<"Book1">>, author => <<"A1">>}),
    _ = create_book(Config, #{title => <<"Book2">>, author => <<"A2">>}),
    Url = base_url(Config) ++ "/books",
    {ok, {{_, 200, _}, _, Body}} = get_req(Url),
    Json = decode_body(Body),
    true = is_list(Json),
    2 = length(Json).

test_list_books_filter_by_author(Config) ->
    _ = create_book(Config, #{title => <<"B1">>, author => <<"Asimov">>}),
    _ = create_book(Config, #{title => <<"B2">>, author => <<"Clarke">>}),
    _ = create_book(Config, #{title => <<"B3">>, author => <<"Asimov">>}),
    Url = base_url(Config) ++ "/books?author=Asimov",
    {ok, {{_, 200, _}, _, Body}} = get_req(Url),
    Json = decode_body(Body),
    2 = length(Json),
    true = lists:all(
        fun(B) -> maps:get(<<"author">>, B) =:= <<"Asimov">> end,
        Json).

test_get_book(Config) ->
    Created = create_book(Config, #{title => <<"T">>, author => <<"A">>}),
    Id = maps:get(<<"id">>, Created),
    Url = base_url(Config) ++ "/books/" ++ binary_to_list(Id),
    {ok, {{_, 200, _}, _, Body}} = get_req(Url),
    Json = decode_body(Body),
    Id = maps:get(<<"id">>, Json),
    <<"T">> = maps:get(<<"title">>, Json).

test_get_not_found(Config) ->
    Url = base_url(Config) ++ "/books/nonexistent",
    {ok, {{_, 404, _}, _, _}} = get_req(Url).

test_update_book(Config) ->
    Created = create_book(Config, #{title => <<"Orig">>,
                                    author => <<"A">>,
                                    year => 2000}),
    Id = maps:get(<<"id">>, Created),
    Url = base_url(Config) ++ "/books/" ++ binary_to_list(Id),
    UpdateBody = encode_body(#{title => <<"Updated">>, year => 2025}),
    {ok, {{_, 200, _}, _, Body}} = put_req(Url, UpdateBody),
    Json = decode_body(Body),
    <<"Updated">> = maps:get(<<"title">>, Json),
    <<"A">> = maps:get(<<"author">>, Json),
    2025 = maps:get(<<"year">>, Json).

test_update_not_found(Config) ->
    Url = base_url(Config) ++ "/books/missing",
    Body = encode_body(#{title => <<"X">>}),
    {ok, {{_, 404, _}, _, _}} = put_req(Url, Body).

test_delete_book(Config) ->
    Created = create_book(Config, #{title => <<"T">>, author => <<"A">>}),
    Id = maps:get(<<"id">>, Created),
    Url = base_url(Config) ++ "/books/" ++ binary_to_list(Id),
    {ok, {{_, 204, _}, _, _}} = delete_req(Url),
    {ok, {{_, 404, _}, _, _}} = get_req(Url).

test_delete_not_found(Config) ->
    Url = base_url(Config) ++ "/books/missing",
    {ok, {{_, 404, _}, _, _}} = delete_req(Url).
