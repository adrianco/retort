-module(bookapi_validator_tests).

-include_lib("eunit/include/eunit.hrl").

%% Unit tests for bookapi_validator module

validate_create_test_() ->
    {setup,
        fun() -> ets:new(book_table, [set, named_table, public]),
            bookapi_db:init([]) end,
        fun(_) -> ets:delete(book_table),
            bookapi_db:terminate(normal, #{}) end,
        [
            {"validate_create_valid_data",
                fun() ->
                    Data = #{title => "Test Book", author => "Test Author",
                             year => 2024, isbn => "978-1234567890"},
                    Result = bookapi_validator:validate_create(Data),
                    ?assertMatch({ok, #{title := "Test Book", author := "Test Author"}}, Result)
                end},
            {"validate_create_empty_title",
                fun() ->
                    Data = #{title => "", author => "Test Author", year => 2024, isbn => "isbn"},
                    Result = bookapi_validator:validate_create(Data),
                    ?assertMatch({error, missing_field}, Result)
                end},
            {"validate_create_missing_title",
                fun() ->
                    Data = #{author => "Test Author", year => 2024, isbn => "isbn"},
                    Result = bookapi_validator:validate_create(Data),
                    ?assertMatch({error, missing_field}, Result)
                end},
            {"validate_create_empty_author",
                fun() ->
                    Data = #{title => "Test Book", author => "", year => 2024, isbn => "isbn"},
                    Result = bookapi_validator:validate_create(Data),
                    ?assertMatch({error, missing_field}, Result)
                end},
            {"validate_create_whitespace_title",
                fun() ->
                    Data = #{title => "   ", author => "Test Author", year => 2024, isbn => "isbn"},
                    Result = bookapi_validator:validate_create(Data),
                    ?assertMatch({error, missing_field}, Result)
                end},
            {"validate_create_whitespace_author",
                fun() ->
                    Data = #{title => "Test Book", author => "   ", year => 2024, isbn => "isbn"},
                    Result = bookapi_validator:validate_create(Data),
                    ?assertMatch({error, missing_field}, Result)
                end},
            {"validate_create_optional_fields",
                fun() ->
                    Data = #{title => "Minimal Book", author => "Author"},
                    Result = bookapi_validator:validate_create(Data),
                    ?assertMatch({ok, #{title := "Minimal Book", author := "Author",
                                         year := undefined, isbn := undefined}}, Result)
                end}
        ]
    }.

validate_update_test_() ->
    {setup,
        fun() -> ets:new(book_table, [set, named_table, public]),
            bookapi_db:init([]) end,
        fun(_) -> ets:delete(book_table),
            bookapi_db:terminate(normal, #{}) end,
        [
            {"validate_update_valid_data",
                fun() ->
                    Data = #{title => "Updated Title", author => "Updated Author"},
                    Result = bookapi_validator:validate_update(Data, 2),
                    ?assertMatch({ok, Data}, Result)
                end},
            {"validate_update_empty_fields",
                fun() ->
                    Data = #{},
                    Result = bookapi_validator:validate_update(Data, 0),
                    ?assertMatch({error, no_fields_to_update}, Result)
                end}
        ]
    }.
