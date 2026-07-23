-module(test_join2).
-export([test/0]).
test() ->
    io:format("Test with string list: ~p~n", [string:join(["a"], ", ")]),
    io:format("Test with empty list: ~p~n", [string:join([], ", ")]),
    io:format("Test with two elements: ~p~n", [string:join(["a", "b"], ", ")]),
    ok.
