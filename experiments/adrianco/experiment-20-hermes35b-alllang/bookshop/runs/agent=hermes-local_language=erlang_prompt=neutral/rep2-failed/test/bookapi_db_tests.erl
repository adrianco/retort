-module(bookapi_db_tests).

-include_lib("eunit/include/eunit.hrl").

%% Unit tests for bookapi_db module

db_seed_data_test_() ->
    {setup,
        fun() -> ets:new(book_table, [set, named_table, public]),
            bookapi_db:init([]) end,
        fun(_) -> ets:delete(book_table),
            bookapi_db:terminate(normal, #{}) end,
        [
            {"db_initial_seeds",
                fun() ->
                    AllBooks = ets:tab2list(book_table),
                    ?assertEqual(3, length(AllBooks)),
                    Titles = lists:map(fun(#book{title = T}) -> T end, AllBooks),
                    ?assert(lists:member("The Great Gatsby", Titles)),
                    ?assert(lists:member("To Kill a Mockingbird", Titles)),
                    ?assert(lists:member("1984", Titles))
                end}
        ]
    }.

db_create_test_() ->
    {setup,
        fun() -> ets:new(book_table, [set, named_table, public]),
            bookapi_db:init([]) end,
        fun(_) -> ets:delete(book_table),
            bookapi_db:terminate(normal, #{}) end,
        [
            {"db_create_valid_book",
                fun() ->
                    Data = #{title => "New Book", author => "New Author",
                             year => 2025, isbn => "978-0000000000"},
                    Result = bookapi_db:create_book(Data),
                    ?assertMatch({ok, #{id := 4, title := "New Book",
                                        author := "New Author", year := 2025, isbn := "978-0000000000"}},
                                 Result)
                end},
            {"db_create_missing_title",
                fun() ->
                    Data = #{author => "Author", year => 2025, isbn => "isbn"},
                    Result = bookapi_db:create_book(Data),
                    ?assertMatch({error, missing_field}, Result)
                end},
            {"db_create_missing_author",
                fun() ->
                    Data = #{title => "Title", year => 2025, isbn => "isbn"},
                    Result = bookapi_db:create_book(Data),
                    ?assertMatch({error, missing_field}, Result)
                end}
        ]
    }.

db_get_test_() ->
    {setup,
        fun() -> ets:new(book_table, [set, named_table, public]),
            bookapi_db:init([]) end,
        fun(_) -> ets:delete(book_table),
            bookapi_db:terminate(normal, #{}) end,
        [
            {"db_get_existing_book",
                fun() ->
                    Result = bookapi_db:get_book(1),
                    ?assertMatch({ok, #{id := 1, title := "The Great Gatsby",
                                        author := "F. Scott Fitzgerald"}},
                                 Result)
                end},
            {"db_get_nonexistent_book",
                fun() ->
                    Result = bookapi_db:get_book(999),
                    ?assertMatch({error, not_found}, Result)
                end}
        ]
    }.

db_list_test_() ->
    {setup,
        fun() -> ets:new(book_table, [set, named_table, public]),
            bookapi_db:init([]) end,
        fun(_) -> ets:delete(book_table),
            bookapi_db:terminate(normal, #{}) end,
        [
            {"db_list_all_books",
                fun() ->
                    Result = bookapi_db:list_books(),
                    ?assert(length(Result) =:= 3),
                    ?assert(is_list(Result))
                end},
            {"db_list_by_author_fitzgerald",
                fun() ->
                    Result = bookapi_db:list_books("F. Scott Fitzgerald"),
                    ?assertEqual(1, length(Result)),
                    ?assertMatch([#{author := "F. Scott Fitzgerald"}], Result)
                end},
            {"db_list_by_author_orwell",
                fun() ->
                    Result = bookapi_db:list_books("George Orwell"),
                    ?assertEqual(1, length(Result)),
                    ?assertMatch([#{author := "George Orwell"}], Result)
                end},
            {"db_list_by_nonexistent_author",
                fun() ->
                    Result = bookapi_db:list_books("Unknown Author"),
                    ?assertEqual(0, length(Result))
                end}
        ]
    }.

db_update_test_() ->
    {setup,
        fun() -> ets:new(book_table, [set, named_table, public]),
            bookapi_db:init([]) end,
        fun(_) -> ets:delete(book_table),
            bookapi_db:terminate(normal, #{}) end,
        [
            {"db_update_existing_book",
                fun() ->
                    Data = #{title => "Updated Title", author => "Updated Author"},
                    Result = bookapi_db:update_book(1, Data),
                    ?assertMatch({ok, #{id := 1, title := "Updated Title",
                                        author := "Updated Author"}},
                                 Result)
                end},
            {"db_update_nonexistent_book",
                fun() ->
                    Data = #{title => "New Title"},
                    Result = bookapi_db:update_book(999, Data),
                    ?assertMatch({error, not_found}, Result)
                end},
            {"db_update_empty_fields",
                fun() ->
                    Result = bookapi_db:update_book(1, #{title => "Updated"}),
                    ?assertMatch({error, no_fields_to_update}, Result)
                end}
        ]
    }.

db_delete_test_() ->
    {setup,
        fun() -> ets:new(book_table, [set, named_table, public]),
            bookapi_db:init([]) end,
        fun(_) -> ets:delete(book_table),
            bookapi_db:terminate(normal, #{}) end,
        [
            {"db_delete_existing_book",
                fun() ->
                    Result = bookapi_db:delete_book(1),
                    ?assertMatch({ok, deleted}, Result),
                    GetResult = bookapi_db:get_book(1),
                    ?assertMatch({error, not_found}, GetResult)
                end},
            {"db_delete_nonexistent_book",
                fun() ->
                    Result = bookapi_db:delete_book(999),
                    ?assertMatch({error, not_found}, Result)
                end}
        ]
    }.
