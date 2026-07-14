-module(book_db_tests).
-export([main/0]).

clean_db() ->
    case whereis(book_db) of
        undefined -> ok;
        _ -> gen_server:stop(book_db)
    end,
    case ets:info(book_db) of
        undefined -> ok;
        _ -> ets:delete(book_db)
    end,
    timer:sleep(200),
    ok.

setup() ->
    clean_db(),
    {ok, _Pid} = book_db:start_link(),
    timer:sleep(200),
    ok.

cleanup() ->
    gen_server:stop(book_db),
    timer:sleep(100),
    ok.

check_true(Expr, Name) ->
    case Expr of
        true -> ok;
        false -> io:format("  [FAIL] ~s: ~p~n", [Name, Expr]), throw(test_failed);
        _ -> io:format("  [FAIL] ~s: ~p~n", [Name, Expr]), throw(test_failed)
    end.

check_equal(Expected, Actual, Name) ->
    case Expected =:= Actual of
        true -> ok;
        false -> io:format("  [FAIL] ~s: expected ~p, got ~p~n", [Name, Expected, Actual]), throw(test_failed)
    end.

%%-------------------------------------------------------------------
%% Test: Create a book
%%-------------------------------------------------------------------
test_create_book() ->
    io:format("  Test: create_book ... "),
    Props = #{title => "Erlang Programming", author => "Joe Armstrong", year => 2013, isbn => "1234567890"},
    {ok, Book} = book_db:create_book(Props),
    Id = maps:get(id, Book),
    check_true(is_integer(Id), "id is integer"),
    check_equal("Erlang Programming", maps:get(title, Book), "title"),
    check_equal("Joe Armstrong", maps:get(author, Book), "author"),
    check_equal(2013, maps:get(year, Book), "year"),
    check_equal("1234567890", maps:get(isbn, Book), "isbn"),
    io:format("[PASS]~n"),
    ok.

%%-------------------------------------------------------------------
%% Test: Get a book by ID
%%-------------------------------------------------------------------
test_get_book() ->
    io:format("  Test: get_book ... "),
    Props = #{title => "Programming Erlang", author => "Austin Clements"},
    {ok, Book1} = book_db:create_book(Props),
    Id = maps:get(id, Book1),
    {ok, Book2} = book_db:get_book(Id),
    check_equal("Programming Erlang", maps:get(title, Book2), "title after get"),
    check_equal("Austin Clements", maps:get(author, Book2), "author after get"),
    case book_db:get_book(9999) of
        {error, not_found} -> ok;
        _ -> io:format("  [FAIL] expected not_found for non-existent id~n"), throw(test_failed)
    end,
    io:format("[PASS]~n"),
    ok.

%%-------------------------------------------------------------------
%% Test: List all books with author filter
%%-------------------------------------------------------------------
test_filter_by_author() ->
    io:format("  Test: filter_by_author ... "),
    book_db:create_book(#{title => "Book A", author => "Author X"}),
    book_db:create_book(#{title => "Book B", author => "Author Y"}),
    book_db:create_book(#{title => "Book C", author => "Author X"}),
    {ok, AllBooks} = book_db:get_all_books(),
    check_equal(3, length(AllBooks), "total book count"),
    {ok, FilteredBooks} = book_db:get_all_books("Author X"),
    check_equal(2, length(FilteredBooks), "filtered book count"),
    io:format("[PASS]~n"),
    ok.

%%-------------------------------------------------------------------
%% Test: Update a book
%%-------------------------------------------------------------------
test_update_book() ->
    io:format("  Test: update_book ... "),
    {ok, Book1} = book_db:create_book(#{title => "Original Title", author => "Author Z"}),
    Id = maps:get(id, Book1),
    {ok, Book2} = book_db:update_book(Id, #{title => "Updated Title", year => 2024}),
    check_equal("Updated Title", maps:get(title, Book2), "updated title"),
    check_equal("Author Z", maps:get(author, Book2), "unchanged author"),
    check_equal(2024, maps:get(year, Book2), "updated year"),
    case book_db:update_book(9999, #{title => "Nope"}) of
        {error, not_found} -> ok;
        _ -> io:format("  [FAIL] expected not_found~n"), throw(test_failed)
    end,
    io:format("[PASS]~n"),
    ok.

%%-------------------------------------------------------------------
%% Test: Delete a book
%%-------------------------------------------------------------------
test_delete_book() ->
    io:format("  Test: delete_book ... "),
    {ok, Book1} = book_db:create_book(#{title => "To Delete", author => "Author"}),
    Id = maps:get(id, Book1),
    {ok, deleted} = book_db:delete_book(Id),
    case book_db:get_book(Id) of
        {error, not_found} -> ok;
        _ -> io:format("  [FAIL] expected not_found after delete~n"), throw(test_failed)
    end,
    case book_db:delete_book(Id) of
        {error, not_found} -> ok;
        _ -> io:format("  [FAIL] expected not_found on double delete~n"), throw(test_failed)
    end,
    io:format("[PASS]~n"),
    ok.

%%-------------------------------------------------------------------
%% Test: Validation - missing title
%%-------------------------------------------------------------------
test_validation_no_title() ->
    io:format("  Test: validation_no_title ... "),
    case book_db:create_book(#{author => "Author"}) of
        {error, "title is required"} -> ok;
        _ -> io:format("  [FAIL] expected title required error~n"), throw(test_failed)
    end,
    case book_db:create_book(#{title => "", author => "Author"}) of
        {error, "title is required"} -> ok;
        _ -> io:format("  [FAIL] expected title required error for empty~n"), throw(test_failed)
    end,
    io:format("[PASS]~n"),
    ok.

%%-------------------------------------------------------------------
%% Test: Validation - missing author
%%-------------------------------------------------------------------
test_validation_no_author() ->
    io:format("  Test: validation_no_author ... "),
    case book_db:create_book(#{title => "Title"}) of
        {error, "author is required"} -> ok;
        _ -> io:format("  [FAIL] expected author required error~n"), throw(test_failed)
    end,
    case book_db:create_book(#{title => "Title", author => ""}) of
        {error, "author is required"} -> ok;
        _ -> io:format("  [FAIL] expected author required error for empty~n"), throw(test_failed)
    end,
    io:format("[PASS]~n"),
    ok.

%%-------------------------------------------------------------------
%% Main
%%-------------------------------------------------------------------
main() ->
    io:format("~n=== book_db unit tests ===~n"),
    case setup() of
        ok ->
            try
                test_create_book(),
                test_get_book(),
                test_filter_by_author(),
                test_update_book(),
                test_delete_book(),
                test_validation_no_title(),
                test_validation_no_author(),
                cleanup(),
                io:format("~nAll 7 unit tests passed!~n"),
                halt(0)
            catch
                Class:Reason ->
                    io:format("~nTest FAILED: ~p:~p~n", [Class, Reason]),
                    cleanup(),
                    halt(1)
            end;
        Error ->
            io:format("Failed to start: ~p~n", [Error]),
            halt(1)
    end.
