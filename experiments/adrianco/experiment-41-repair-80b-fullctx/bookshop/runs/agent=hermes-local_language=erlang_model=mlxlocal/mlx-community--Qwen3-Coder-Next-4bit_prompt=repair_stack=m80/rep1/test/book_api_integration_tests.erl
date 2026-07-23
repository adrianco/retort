-module(book_api_integration_tests).

-include_lib("eunit/include/eunit.hrl").

% Integration tests for book API endpoints

% Setup and teardown to start the database server only
setup() ->
    application:load(book_api),
    {ok, _} = book_api_db:start_link(),
    ok.

cleanup(_) ->
    gen_server:stop(book_api_db),
    ok.

books_endpoint_test_() ->
    {setup,
        fun setup/0,
        fun cleanup/1,
        [
            {"POST /books creates a new book",
                fun() ->
                    {ok, Book} = book_api_db:create_book(#{title => <<"Integration Test">>, author => <<"Test Author">>}),
                    ?assert(is_map(Book)),
                    ?assertEqual(1, maps:get(id, Book)),
                    ?assertEqual(<<"Integration Test">>, maps:get(title, Book)),
                    ?assertEqual(<<"Test Author">>, maps:get(author, Book)),
                    ok
                end},
            {"GET /books lists all books",
                fun() ->
                    {ok, Books} = book_api_db:get_all_books(),
                    ?assert(is_list(Books)),
                    ?assert(length(Books) >= 1),
                    ok
                end}
        ]
    }.

book_by_id_endpoint_test_() ->
    {setup,
        fun setup/0,
        fun cleanup/1,
        [
            {"GET /books/1 gets a single book",
                fun() ->
                    {ok, Book} = book_api_db:get_book_by_id(1),
                    ?assert(is_map(Book)),
                    ?assertEqual(1, maps:get(id, Book)),
                    ok
                end},
            {"PUT /books/1 updates a book",
                fun() ->
                    {ok, Book} = book_api_db:update_book(1, #{title => <<"Updated via API">>}),
                    ?assertEqual(<<"Updated via API">>, maps:get(title, Book)),
                    ok
                end},
            {"DELETE /books/1 deletes a book",
                fun() ->
                    ok = book_api_db:delete_book(1),
                    {error, not_found} = book_api_db:get_book_by_id(1),
                    ok
                end}
        ]
    }.
