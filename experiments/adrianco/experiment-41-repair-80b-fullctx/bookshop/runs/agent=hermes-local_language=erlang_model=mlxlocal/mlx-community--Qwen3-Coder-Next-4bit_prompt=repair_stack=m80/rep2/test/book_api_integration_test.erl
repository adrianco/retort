%% Additional integration tests
-module(book_api_integration_test).

-include_lib("eunit/include/eunit.hrl").

%% Test that the application starts correctly
start_test_() ->
    {setup,
        fun() -> application:start(crypto) end,
        fun(_) -> application:stop(crypto) end,
        fun() ->
            %% Try to start the app
            case application:start(book_api) of
                ok -> ?assert(true);
                {error, {already_started, book_api}} -> ?assert(true)
            end
        end
    }.

%% Test book validation edge cases
book_validation_edge_cases_tests_() ->
    {setup,
        fun() -> ok end,
        fun(_) -> ok end,
        [
            fun book_validation_with_null_year/0,
            fun book_validation_with_null_isbn/0,
            fun book_validation_with_both_null/0
        ]}.

book_validation_with_null_year() ->
    Book = #{title => <<"Book">>, author => <<"Author">>, year => null},
    {ok, Result} = book:validate(Book),
    ?assert(is_map(Result)),
    ?assertEqual(null, maps:get(year, Result)).

book_validation_with_null_isbn() ->
    Book = #{title => <<"Book">>, author => <<"Author">>, isbn => null},
    {ok, Result} = book:validate(Book),
    ?assert(is_map(Result)),
    ?assertEqual(null, maps:get(isbn, Result)).

book_validation_with_both_null() ->
    Book = #{title => <<"Book">>, author => <<"Author">>, year => null, isbn => null},
    {ok, Result} = book:validate(Book),
    ?assert(is_map(Result)).

%% Test invalid input handling
invalid_input_tests_() ->
    {setup,
        fun() -> ok end,
        fun(_) -> ok end,
        [
            fun book_validate_not_map/0,
            fun book_parse_json_not_map/0,
            fun db_get_book_by_id_invalid/0,
            fun db_update_book_invalid_id/0,
            fun db_delete_book_invalid_id/0
        ]}.

book_validate_not_map() ->
    ?assertEqual({error, invalid_data}, book:validate("not a map")),
    ?assertEqual({error, invalid_data}, book:validate([1,2,3])),
    ?assertEqual({error, invalid_data}, book:validate(123)).

book_parse_json_not_map() ->
    ?assertMatch({error, _}, book:parse_json("not a map")),
    ?assertMatch({error, _}, book:parse_json([1,2,3])).

db_get_book_by_id_invalid() ->
    ?assertEqual({error, invalid_id}, book_api_db:get_book_by_id("not-an-integer")),
    ?assertEqual({error, invalid_id}, book_api_db:get_book_by_id([])).

db_update_book_invalid_id() ->
    ?assertEqual({error, invalid_id}, book_api_db:update_book("not-an-integer", #{title => <<"Test">>})),
    ?assertEqual({error, invalid_id}, book_api_db:update_book([], #{title => <<"Test">>})).

db_delete_book_invalid_id() ->
    ?assertEqual({error, invalid_id}, book_api_db:delete_book("not-an-integer")),
    ?assertEqual({error, invalid_id}, book_api_db:delete_book([])).
