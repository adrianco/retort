-module(books_handler_tests).
-include_lib("eunit/include/eunit.hrl").

validate_ok_test() ->
    ?assertEqual(ok, books_handler:validate(#{
        <<"title">> => <<"T">>,
        <<"author">> => <<"A">>
    })).

validate_missing_title_test() ->
    ?assertMatch({error, _}, books_handler:validate(#{
        <<"author">> => <<"A">>
    })).

validate_missing_author_test() ->
    ?assertMatch({error, _}, books_handler:validate(#{
        <<"title">> => <<"T">>
    })).

validate_empty_title_test() ->
    ?assertMatch({error, _}, books_handler:validate(#{
        <<"title">> => <<>>,
        <<"author">> => <<"A">>
    })).

validate_empty_author_test() ->
    ?assertMatch({error, _}, books_handler:validate(#{
        <<"title">> => <<"T">>,
        <<"author">> => <<>>
    })).

validate_non_binary_title_test() ->
    ?assertMatch({error, _}, books_handler:validate(#{
        <<"title">> => 123,
        <<"author">> => <<"A">>
    })).
