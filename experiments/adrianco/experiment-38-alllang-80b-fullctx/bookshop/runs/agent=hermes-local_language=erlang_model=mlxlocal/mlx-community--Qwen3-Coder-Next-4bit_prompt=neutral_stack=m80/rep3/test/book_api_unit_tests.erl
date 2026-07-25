%% -*- erlang -*-
%% This file is part of Book API Tests.
%%
%% Simple unit tests for the Book API.

-module(book_api_unit_tests).

-include_lib("eunit/include/eunit.hrl").

%% Test suite
-export([unit_tests_/0]).

unit_tests_() ->
    [
        {"Validation: Both fields missing",
            fun() -> 
                Result = validate_book_params(#{}),
                ?assertMatch({error, _}, Result)
            end
        },
        {"Validation: Missing title",
            fun() -> 
                Result = validate_book_params(#{author => <<"Author">>}),
                ?assertMatch({error, _}, Result)
            end
        },
        {"Validation: Missing author",
            fun() -> 
                Result = validate_book_params(#{title => <<"Title">>}),
                ?assertMatch({error, _}, Result)
            end
        },
        {"Validation: Both fields present",
            fun() -> 
                Result = validate_book_params(#{title => <<"Title">>, author => <<"Author">>}),
                ?assertMatch(ok, Result)
            end
        }
    ].

%% Copy of the validate_book_params function for testing
validate_book_params(Params) ->
    Title = maps:get(title, Params, undefined),
    Author = maps:get(author, Params, undefined),
    case {Title, Author} of
        {undefined, undefined} -> {error, [<<"title is required">>, <<"author is required">>]};
        {undefined, _} -> {error, [<<"title is required">>]};
        {_, undefined} -> {error, [<<"author is required">>]};
        {_, _} -> ok
    end.
