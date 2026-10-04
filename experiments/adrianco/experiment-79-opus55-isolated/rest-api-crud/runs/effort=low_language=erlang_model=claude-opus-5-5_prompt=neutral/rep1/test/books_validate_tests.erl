-module(books_validate_tests).

-include_lib("eunit/include/eunit.hrl").

valid_test() ->
    ?assertEqual({ok, #{title => <<"T">>, author => <<"A">>, year => 2000, isbn => <<"1">>}},
                 books_handler:validate(#{<<"title">> => <<"T">>, <<"author">> => <<"A">>,
                                          <<"year">> => 2000, <<"isbn">> => <<"1">>})).

optional_fields_default_to_null_test() ->
    ?assertEqual({ok, #{title => <<"T">>, author => <<"A">>, year => null, isbn => null}},
                 books_handler:validate(#{<<"title">> => <<"T">>, <<"author">> => <<"A">>})).

missing_required_test() ->
    ?assertEqual({error, [<<"title is required">>, <<"author is required">>]},
                 books_handler:validate(#{})).

blank_title_test() ->
    ?assertEqual({error, [<<"title is required">>]},
                 books_handler:validate(#{<<"title">> => <<"   ">>, <<"author">> => <<"A">>})).

wrong_types_test() ->
    ?assertEqual({error, [<<"author must be a string">>, <<"year must be an integer">>]},
                 books_handler:validate(#{<<"title">> => <<"T">>, <<"author">> => 7,
                                          <<"year">> => 19.5})).

non_object_test() ->
    ?assertMatch({error, [_]}, books_handler:validate([])).
