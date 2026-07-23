-module(test_join).
-export([test/0]).
test() ->
    io:format("Test 1: ~p~n", [string:join(["a", "b"], ", ")]),
    io:format("Test 2: ~p~n", [string:join(["a"], ", ")]),
    io:format("Test 3: ~p~n", [string:join([], ", ")]),
    io:format("Test 4: ~p~n", [string:join([<<"a">>], ", ")]),
    ok.
