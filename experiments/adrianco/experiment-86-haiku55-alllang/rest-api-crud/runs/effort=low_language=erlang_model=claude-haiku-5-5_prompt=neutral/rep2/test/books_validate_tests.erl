-module(books_validate_tests).
-include_lib("eunit/include/eunit.hrl").

accepts_minimal_book_test() ->
    ?assertEqual({ok, #{title => <<"Dune">>, author => <<"Frank Herbert">>,
                        year => null, isbn => null}},
                 books_validate:validate(#{<<"title">> => <<"Dune">>,
                                           <<"author">> => <<"Frank Herbert">>})).

accepts_full_book_test() ->
    ?assertMatch({ok, #{year := 1965, isbn := <<"978-0441172719">>}},
                 books_validate:validate(#{<<"title">> => <<"Dune">>,
                                           <<"author">> => <<"Frank Herbert">>,
                                           <<"year">> => 1965,
                                           <<"isbn">> => <<"978-0441172719">>})).

trims_surrounding_whitespace_test() ->
    ?assertMatch({ok, #{title := <<"Dune">>}},
                 books_validate:validate(#{<<"title">> => <<"  Dune ">>,
                                           <<"author">> => <<"Frank Herbert">>})).

missing_title_is_rejected_test() ->
    ?assertEqual({error, [<<"title is required">>]},
                 books_validate:validate(#{<<"author">> => <<"Frank Herbert">>})).

blank_author_is_rejected_test() ->
    ?assertEqual({error, [<<"author is required">>]},
                 books_validate:validate(#{<<"title">> => <<"Dune">>,
                                           <<"author">> => <<"   ">>})).

non_string_title_is_rejected_test() ->
    ?assertEqual({error, [<<"title must be a string">>]},
                 books_validate:validate(#{<<"title">> => 42,
                                           <<"author">> => <<"Frank Herbert">>})).

bad_year_is_rejected_test() ->
    ?assertMatch({error, [<<"year must be an integer", _/binary>>]},
                 books_validate:validate(#{<<"title">> => <<"Dune">>,
                                           <<"author">> => <<"Frank Herbert">>,
                                           <<"year">> => <<"1965">>})).

out_of_range_year_is_rejected_test() ->
    ?assertMatch({error, [_]},
                 books_validate:validate(#{<<"title">> => <<"Dune">>,
                                           <<"author">> => <<"Frank Herbert">>,
                                           <<"year">> => 12345})).

bad_isbn_is_rejected_test() ->
    ?assertMatch({error, [<<"isbn must be", _/binary>>]},
                 books_validate:validate(#{<<"title">> => <<"Dune">>,
                                           <<"author">> => <<"Frank Herbert">>,
                                           <<"isbn">> => <<"not-an-isbn!">>})).

reports_all_errors_together_test() ->
    ?assertMatch({error, [_, _, _]},
                 books_validate:validate(#{<<"year">> => <<"x">>})).

non_object_body_is_rejected_test() ->
    ?assertMatch({error, [_]}, books_validate:validate([1, 2, 3])).
