%% Pure input validation for book create/update payloads.
-module(books_validate).

-export([validate/1]).

%% Returns normalised attributes (title and author trimmed, year and isbn
%% null when omitted) or the list of human-readable error messages.
-spec validate(term()) -> {ok, map()} | {error, [binary()]}.
validate(Body) when is_map(Body) ->
    Fields = [{title, required_string(<<"title">>, Body)},
              {author, required_string(<<"author">>, Body)},
              {year, optional_year(Body)},
              {isbn, optional_string(<<"isbn">>, Body)}],
    case [Msg || {_, {error, Msg}} <- Fields] of
        [] -> {ok, maps:from_list([{K, V} || {K, {ok, V}} <- Fields])};
        Errors -> {error, Errors}
    end;
validate(_) ->
    {error, [<<"request body must be a JSON object">>]}.

required_string(Key, Body) ->
    case maps:get(Key, Body, missing) of
        missing -> {error, <<Key/binary, " is required">>};
        Value when is_binary(Value) ->
            case string:trim(Value) of
                <<>> -> {error, <<Key/binary, " must not be empty">>};
                Trimmed -> {ok, Trimmed}
            end;
        _ -> {error, <<Key/binary, " must be a string">>}
    end.

optional_string(Key, Body) ->
    case maps:get(Key, Body, null) of
        null -> {ok, null};
        Value when is_binary(Value) -> {ok, Value};
        _ -> {error, <<Key/binary, " must be a string">>}
    end.

optional_year(Body) ->
    case maps:get(<<"year">>, Body, null) of
        null -> {ok, null};
        Year when is_integer(Year), Year >= 0 -> {ok, Year};
        _ -> {error, <<"year must be a non-negative integer">>}
    end.
