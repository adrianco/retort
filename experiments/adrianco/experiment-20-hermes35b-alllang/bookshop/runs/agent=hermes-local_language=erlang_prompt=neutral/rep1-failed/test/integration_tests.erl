-module(integration_tests).
-export([main/0]).

-define(PORT, 8765).

clean_env() ->
    application:stop(book_api),
    application:stop(cowboy),
    application:stop(jiffy),
    application:stop(inets),
    timer:sleep(500),
    case whereis(book_db) of
        undefined -> ok;
        _ -> gen_server:stop(book_db)
    end,
    case ets:info(book_db) of
        undefined -> ok;
        _ -> ets:delete(book_db)
    end,
    timer:sleep(300),
    ok.

setup() ->
    clean_env(),
    application:start(kernel),
    application:start(stdlib),
    application:start(inets),
    application:start(jiffy),
    application:start(cowboy),
    application:start(book_api),
    timer:sleep(500),
    ok.

teardown() ->
    application:stop(book_api),
    application:stop(cowboy),
    application:stop(jiffy),
    timer:sleep(200),
    ok.

http_get(Url) ->
    {ok, {{_, StatusCode, _}, _Headers, Body}} =
        inets:httpc:request(get, {Url, []}, [], []),
    {StatusCode, Body}.

http_post(Url, Body) ->
    Headers = [{"content-type", "application/json"}],
    {ok, {{_, StatusCode, _}, _RespHeaders, RespBody}} =
        inets:httpc:request(post, {Url, Headers}, [], Body, []),
    {StatusCode, RespBody}.

http_put(Url, Body) ->
    Headers = [{"content-type", "application/json"}],
    {ok, {{_, StatusCode, _}, _RespHeaders, RespBody}} =
        inets:httpc:request(put, {Url, Headers}, [], Body, []),
    {StatusCode, RespBody}.

http_delete(Url) ->
    {ok, {{_, StatusCode, _}, _Headers, Body}} =
        inets:httpc:request(delete, {Url, []}, [], []),
    {StatusCode, Body}.

check(Description, Expected, Actual) ->
    case {Expected, Actual} of
        {Expected, Expected} ->
            io:format("  [PASS] ~s~n", [Description]),
            ok;
        _ ->
            io:format("  [FAIL] ~s: expected ~p, got ~p~n", [Description, Expected, Actual]),
            throw(test_failed)
    end.

test_health() ->
    io:format("  Test: health check ... "),
    Url = "http://localhost:" ++ integer_to_list(?PORT) ++ "/health",
    {200, Body} = http_get(Url),
    Decoded = jiffy:decode(Body),
    #{status := "ok"} = Decoded,
    io:format("[PASS]~n"),
    ok.

test_create_and_get_book() ->
    io:format("  Test: create and get book ... "),
    book_db:delete_all(),
    timer:sleep(100),
    Json = jiffy:encode(#{
        title => "The BEAM Book",
        author => "Ulf Wiger",
        year => 2021,
        isbn => "978-0995445752"
    }),
    Url = "http://localhost:" ++ integer_to_list(?PORT) ++ "/books",
    {201, Resp} = http_post(Url, Json),
    #{id := Id} = jiffy:decode(Resp),
    check(true, is_integer(Id), "response has integer id"),
    GetUrl = "http://localhost:" ++ integer_to_list(?PORT) ++ "/books/" ++ integer_to_list(Id),
    {200, Body} = http_get(GetUrl),
    #{title := "The BEAM Book", author := "Ulf Wiger"} = jiffy:decode(Body),
    ok.

test_list_and_filter_books() ->
    io:format("  Test: list and filter books ... "),
    book_db:delete_all(),
    timer:sleep(100),
    book_db:create_book(#{title => "Book 1", author => "Alice", year => 2020}),
    book_db:create_book(#{title => "Book 2", author => "Bob", year => 2021}),
    book_db:create_book(#{title => "Book 3", author => "Alice", year => 2022}),
    timer:sleep(100),
    Url = "http://localhost:" ++ integer_to_list(?PORT) ++ "/books",
    {200, Body} = http_get(Url),
    #{books := Books} = jiffy:decode(Body),
    check(3, length(Books), "lists all 3 books"),
    FilterUrl = "http://localhost:" ++ integer_to_list(?PORT) ++ "/books?author=Alice",
    {200, Filtered} = http_get(FilterUrl),
    #{books := FilteredBooks} = jiffy:decode(Filtered),
    check(2, length(FilteredBooks), "filters to 2 books for Alice"),
    ok.

test_update_book() ->
    io:format("  Test: update book ... "),
    book_db:delete_all(),
    timer:sleep(100),
    {ok, Book} = book_db:create_book(#{title => "Original", author => "Author", year => 2019}),
    Id = maps:get(id, Book),
    UpdateUrl = "http://localhost:" ++ integer_to_list(?PORT) ++ "/books/" ++ integer_to_list(Id),
    UpdateJson = jiffy:encode(#{title => "Updated Title"}),
    {200, Resp} = http_put(UpdateUrl, UpdateJson),
    #{title := "Updated Title"} = jiffy:decode(Resp),
    {200, Body} = http_get(UpdateUrl),
    #{title := "Updated Title", author := "Author"} = jiffy:decode(Body),
    ok.

test_delete_book() ->
    io:format("  Test: delete book ... "),
    book_db:delete_all(),
    timer:sleep(100),
    {ok, Book} = book_db:create_book(#{title => "To Delete", author => "Author"}),
    Id = maps:get(id, Book),
    DelUrl = "http://localhost:" ++ integer_to_list(?PORT) ++ "/books/" ++ integer_to_list(Id),
    {200, _Resp} = http_delete(DelUrl),
    {404, _Body} = http_get(DelUrl),
    ok.

test_validation_errors() ->
    io:format("  Test: validation errors ... "),
    book_db:delete_all(),
    timer:sleep(100),
    Url = "http://localhost:" ++ integer_to_list(?PORT) ++ "/books",
    MissingTitle = jiffy:encode(#{author => "Author"}),
    {400, Resp} = http_post(Url, MissingTitle),
    #{error := _} = jiffy:decode(Resp),
    MissingAuthor = jiffy:encode(#{title => "Title"}),
    {400, Resp2} = http_post(Url, MissingAuthor),
    #{error := _} = jiffy:decode(Resp2),
    ok.

%%-------------------------------------------------------------------
%% Main
%%-------------------------------------------------------------------
main() ->
    io:format("~n=== Integration tests ===~n"),
    case setup() of
        ok ->
            try
                test_health(),
                test_create_and_get_book(),
                test_list_and_filter_books(),
                test_update_book(),
                test_delete_book(),
                test_validation_errors(),
                teardown(),
                io:format("~nAll integration tests passed!~n"),
                halt(0)
            catch
                Class:Reason ->
                    io:format("~nIntegration test FAILED: ~p:~p~n", [Class, Reason]),
                    teardown(),
                    halt(1)
            end;
        Error ->
            io:format("Failed to start: ~p~n", [Error]),
            halt(1)
    end.
