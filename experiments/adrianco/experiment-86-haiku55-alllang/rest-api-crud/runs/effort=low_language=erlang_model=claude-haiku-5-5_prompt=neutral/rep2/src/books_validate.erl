%% Validation and normalisation of book payloads.
-module(books_validate).

-export([validate/1]).

%% Returns {ok, Attrs} with normalised fields (title, author, year, isbn),
%% or {error, Messages} listing every problem found.
-spec validate(term()) -> {ok, map()} | {error, [binary()]}.
validate(Params) when is_map(Params) ->
    Errors = lists:append([
        required_text(Params, <<"title">>),
        required_text(Params, <<"author">>),
        year_errors(Params),
        isbn_errors(Params)
    ]),
    case Errors of
        [] -> {ok, normalise(Params)};
        _ -> {error, Errors}
    end;
validate(_) ->
    {error, [<<"request body must be a JSON object">>]}.

required_text(Params, Key) ->
    case field(Params, Key) of
        null ->
            [<<Key/binary, " is required">>];
        Value when is_binary(Value) ->
            case string:is_empty(string:trim(Value)) of
                true -> [<<Key/binary, " is required">>];
                false -> []
            end;
        _ ->
            [<<Key/binary, " must be a string">>]
    end.

year_errors(Params) ->
    case field(Params, <<"year">>) of
        null -> [];
        Year when is_integer(Year), Year >= 0, Year =< 9999 -> [];
        _ -> [<<"year must be an integer between 0 and 9999">>]
    end.

isbn_errors(Params) ->
    case field(Params, <<"isbn">>) of
        null -> [];
        Isbn when is_binary(Isbn) ->
            case re:run(Isbn, <<"^[0-9Xx-]{10,17}$">>, [{capture, none}]) of
                match -> [];
                nomatch -> [<<"isbn must be 10 to 17 characters of digits, hyphens or X">>]
            end;
        _ -> [<<"isbn must be a string">>]
    end.

normalise(Params) ->
    #{title => text(field(Params, <<"title">>)),
      author => text(field(Params, <<"author">>)),
      year => field(Params, <<"year">>),
      isbn => isbn(field(Params, <<"isbn">>))}.

isbn(null) -> null;
isbn(Isbn) -> Isbn.

text(Value) ->
    unicode:characters_to_binary(string:trim(Value)).

%% Missing and null fields are treated the same.
field(Params, Key) ->
    maps:get(Key, Params, null).
