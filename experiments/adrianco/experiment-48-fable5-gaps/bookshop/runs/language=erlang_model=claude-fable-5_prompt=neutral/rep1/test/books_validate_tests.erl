%% Unit tests for the validation module.
-module(books_validate_tests).

-include_lib("eunit/include/eunit.hrl").

valid_full_book_test() ->
    {ok, Clean} = books_validate:book(#{<<"title">> => <<"Dune">>,
                                        <<"author">> => <<"Frank Herbert">>,
                                        <<"year">> => 1965,
                                        <<"isbn">> => <<"978-0441172719">>}),
    ?assertEqual(#{title => <<"Dune">>, author => <<"Frank Herbert">>,
                   year => 1965, isbn => <<"978-0441172719">>}, Clean).

optional_fields_default_to_null_test() ->
    {ok, Clean} = books_validate:book(#{<<"title">> => <<"T">>,
                                        <<"author">> => <<"A">>}),
    ?assertEqual(null, maps:get(year, Clean)),
    ?assertEqual(null, maps:get(isbn, Clean)).

title_is_trimmed_test() ->
    {ok, Clean} = books_validate:book(#{<<"title">> => <<"  T  ">>,
                                        <<"author">> => <<"A">>}),
    ?assertEqual(<<"T">>, maps:get(title, Clean)).

missing_required_fields_test() ->
    {error, Errors} = books_validate:book(#{}),
    ?assertEqual([<<"title is required">>, <<"author is required">>], Errors).

wrong_types_test() ->
    {error, Errors} = books_validate:book(#{<<"title">> => 42,
                                            <<"author">> => <<"A">>,
                                            <<"year">> => <<"1990">>,
                                            <<"isbn">> => 5}),
    ?assert(lists:member(<<"title must be a string">>, Errors)),
    ?assert(lists:member(<<"year must be an integer">>, Errors)),
    ?assert(lists:member(<<"isbn must be a string">>, Errors)).
