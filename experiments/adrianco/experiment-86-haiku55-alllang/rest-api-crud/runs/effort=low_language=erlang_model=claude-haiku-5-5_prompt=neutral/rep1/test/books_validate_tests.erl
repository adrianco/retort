-module(books_validate_tests).

-include_lib("eunit/include/eunit.hrl").

valid_payload_test() ->
    ?assertEqual({ok, #{title => <<"Dune">>, author => <<"Frank Herbert">>,
                        year => 1965, isbn => <<"9780441172719">>}},
                 books_validate:validate(#{<<"title">> => <<"Dune">>,
                                           <<"author">> => <<"Frank Herbert">>,
                                           <<"year">> => 1965,
                                           <<"isbn">> => <<"9780441172719">>})).

optional_fields_default_to_null_test() ->
    ?assertEqual({ok, #{title => <<"Dune">>, author => <<"Frank Herbert">>,
                        year => null, isbn => null}},
                 books_validate:validate(#{<<"title">> => <<"Dune">>,
                                           <<"author">> => <<"Frank Herbert">>})).

title_and_author_are_trimmed_test() ->
    ?assertEqual({ok, #{title => <<"Dune">>, author => <<"Herbert">>,
                        year => null, isbn => null}},
                 books_validate:validate(#{<<"title">> => <<"  Dune ">>,
                                           <<"author">> => <<"Herbert">>})).

missing_required_fields_test() ->
    ?assertEqual({error, [<<"title is required">>, <<"author is required">>]},
                 books_validate:validate(#{})).

blank_required_fields_test() ->
    ?assertEqual({error, [<<"title must not be empty">>, <<"author must not be empty">>]},
                 books_validate:validate(#{<<"title">> => <<"   ">>,
                                           <<"author">> => <<>>})).

wrong_types_test() ->
    ?assertEqual({error, [<<"title must be a string">>,
                          <<"year must be a non-negative integer">>,
                          <<"isbn must be a string">>]},
                 books_validate:validate(#{<<"title">> => 42,
                                           <<"author">> => <<"A">>,
                                           <<"year">> => <<"1965">>,
                                           <<"isbn">> => 123})).

negative_year_rejected_test() ->
    ?assertMatch({error, [<<"year must be a non-negative integer">>]},
                 books_validate:validate(#{<<"title">> => <<"T">>,
                                           <<"author">> => <<"A">>,
                                           <<"year">> => -1})).

non_object_body_test() ->
    ?assertEqual({error, [<<"request body must be a JSON object">>]},
                 books_validate:validate([1, 2, 3])).
