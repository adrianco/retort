-module(book_api_tests).

-export([run_tests/0]).

run_tests() ->
    io:format("Running book_api unit tests...~n"),
    case eunit:test(book_api_db_tests) of
        ok -> io:format("Unit tests passed~n");
        Error -> io:format("Unit tests failed: ~p~n", [Error])
    end,
    io:format("Running book_api integration tests...~n"),
    case eunit:test(book_api_integration_tests) of
        ok -> io:format("Integration tests passed~n");
        Error1 -> io:format("Integration tests failed: ~p~n", [Error1])
    end,
    ok.
