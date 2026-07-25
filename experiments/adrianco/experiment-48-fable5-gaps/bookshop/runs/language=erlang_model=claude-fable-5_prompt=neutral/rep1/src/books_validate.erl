%% Input validation for book payloads.
%% Required: title, author (non-empty strings).
%% Optional: year (integer), isbn (string) — stored as null when absent.
-module(books_validate).

-export([book/1]).

-spec book(map()) -> {ok, map()} | {error, [binary()]}.
book(Fields) ->
    {Title, E1} = required_string(<<"title">>, Fields, []),
    {Author, E2} = required_string(<<"author">>, Fields, E1),
    {Year, E3} = optional_integer(<<"year">>, Fields, E2),
    {Isbn, E4} = optional_string(<<"isbn">>, Fields, E3),
    case E4 of
        [] ->
            {ok, #{title => Title, author => Author, year => Year, isbn => Isbn}};
        Errors ->
            {error, lists:reverse(Errors)}
    end.

required_string(Key, Fields, Errors) ->
    case maps:get(Key, Fields, undefined) of
        Value when is_binary(Value) ->
            case string:trim(Value) of
                <<>> -> {undefined, [<<Key/binary, " must not be empty">> | Errors]};
                Trimmed -> {Trimmed, Errors}
            end;
        undefined ->
            {undefined, [<<Key/binary, " is required">> | Errors]};
        null ->
            {undefined, [<<Key/binary, " is required">> | Errors]};
        _ ->
            {undefined, [<<Key/binary, " must be a string">> | Errors]}
    end.

optional_integer(Key, Fields, Errors) ->
    case maps:get(Key, Fields, undefined) of
        undefined -> {null, Errors};
        null -> {null, Errors};
        Value when is_integer(Value) -> {Value, Errors};
        _ -> {null, [<<Key/binary, " must be an integer">> | Errors]}
    end.

optional_string(Key, Fields, Errors) ->
    case maps:get(Key, Fields, undefined) of
        undefined -> {null, Errors};
        null -> {null, Errors};
        Value when is_binary(Value) -> {Value, Errors};
        _ -> {null, [<<Key/binary, " must be a string">> | Errors]}
    end.
