-module(book_api_db_tests).

-include_lib("eunit/include/eunit.hrl").

% Unit tests for book_api_db module

% Setup and teardown to start/stop the database server
setup() ->
    %% Stop and clean up if running
    case whereis(book_api_sup) of
        undefined -> ok;
        Pid -> exit(Pid, kill), timer:sleep(100)
    end,
    %% Clean up any existing database
    DbPath = "books.db",
    file:delete(DbPath),
    %% Start fresh
    application:load(book_api),
    {ok, _} = application:ensure_all_started(book_api),
    %% Wait for db to be initialized
    timer:sleep(100),
    ok.

cleanup(_) ->
    gen_server:stop(book_api_db),
    ok.

create_book_test_() ->
    {setup,
        fun setup/0,
        fun cleanup/1,
        [
            {"Create book with valid data",
                fun() ->
                    {ok, Book} = book_api_db:create_book(#{title => <<"Test Book">>, author => <<"Test Author">>}),
                    ?assert(is_map(Book)),
                    ?assertEqual(1, maps:get(id, Book)),
                    ?assertEqual(<<"Test Book">>, maps:get(title, Book)),
                    ?assertEqual(<<"Test Author">>, maps:get(author, Book)),
                    ok
                end}
        ]
    }.

get_all_books_test_() ->
    {setup,
        fun setup/0,
        fun cleanup/1,
        [
            {"Get all books",
                fun() ->
                    {ok, Books} = book_api_db:get_all_books(),
                    ?assert(is_list(Books)),
                    ?assert(length(Books) >= 1),
                    ok
                end}
        ]
    }.

get_book_by_id_test_() ->
    {setup,
        fun setup/0,
        fun cleanup/1,
        [
            {"Get existing book by id",
                fun() ->
                    {ok, Book} = book_api_db:get_book_by_id(1),
                    ?assert(is_map(Book)),
                    ?assertEqual(<<"Test Book">>, maps:get(title, Book)),
                    ok
                end},
            {"Get non-existing book by id",
                fun() ->
                    {error, not_found} = book_api_db:get_book_by_id(9999),
                    ok
                end}
        ]
    }.

update_book_test_() ->
    {setup,
        fun setup/0,
        fun cleanup/1,
        [
            {"Update existing book",
                fun() ->
                    {ok, Book} = book_api_db:update_book(1, #{title => <<"Updated Title">>}),
                    ?assertEqual(<<"Updated Title">>, maps:get(title, Book)),
                    ok
                end},
            {"Update non-existing book should fail",
                fun() ->
                    {error, not_found} = book_api_db:update_book(9999, #{title => <<"Updated Title">>}),
                    ok
                end},
            {"Update without changes should fail",
                fun() ->
                    {error, no_changes} = book_api_db:update_book(1, #{}),
                    ok
                end}
        ]
    }.

delete_book_test_() ->
    {setup,
        fun setup/0,
        fun cleanup/1,
        [
            {"Delete existing book",
                fun() ->
                    ok = book_api_db:delete_book(1),
                    ok
                end},
            {"Delete non-existing book should fail",
                fun() ->
                    {error, not_found} = book_api_db:delete_book(9999),
                    ok
                end}
        ]
    }.

health_check_test_() ->
    {setup,
        fun setup/0,
        fun cleanup/1,
        [
            {"Health check should return healthy",
                fun() ->
                    {ok, healthy} = book_api_db:health_check(),
                    ok
                end}
        ]
    }.
