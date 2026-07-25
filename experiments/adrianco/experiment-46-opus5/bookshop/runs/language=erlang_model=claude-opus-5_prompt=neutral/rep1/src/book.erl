%%%-------------------------------------------------------------------
%%% @doc Pure book domain logic: validation of incoming JSON payloads and
%%% rendering of stored books back to JSON-friendly maps.
%%%
%%% This module has no side effects, which makes the validation rules
%%% cheap to unit test without a database or a running server.
%%% @end
%%%-------------------------------------------------------------------
-module(book).

-include("book_api.hrl").

-export([validate/1, to_map/1, matches_author/2]).

-export_type([errors/0, attrs/0]).

-define(MAX_TEXT_LEN, 512).
-define(MIN_YEAR, -3000).
-define(MAX_YEAR, 2999).

-type attrs() :: #{title := binary(),
                   author := binary(),
                   year := integer() | null,
                   isbn := binary() | null}.

%% One error per offending field, in a stable (declaration) order.
-type errors() :: [#{binary() => binary()}].

%%%===================================================================
%%% API
%%%===================================================================

%% @doc Validate a decoded JSON body and normalise it into book attributes.
%%
%% `title' and `author' are required and must be non-blank strings.
%% `year' and `isbn' are optional; they may be omitted or explicitly null.
-spec validate(term()) -> {ok, attrs()} | {error, errors()}.
validate(Body) when is_map(Body) ->
    Results = [{title,  text(<<"title">>, Body, required)},
               {author, text(<<"author">>, Body, required)},
               {year,   year(Body)},
               {isbn,   isbn(Body)}],
    case [E || {_, {error, E}} <- Results] of
        [] ->
            {ok, maps:from_list([{K, V} || {K, {ok, V}} <- Results])};
        Errors ->
            {error, Errors}
    end;
validate(_NotAnObject) ->
    {error, [err(<<"body">>, <<"must be a JSON object">>)]}.

%% @doc Render a stored book as a map ready for `json:encode/1'.
-spec to_map(#book{}) -> map().
to_map(#book{id = Id, title = Title, author = Author, year = Year,
             isbn = Isbn, created_at = Created, updated_at = Updated}) ->
    #{<<"id">> => Id,
      <<"title">> => Title,
      <<"author">> => Author,
      <<"year">> => Year,
      <<"isbn">> => Isbn,
      <<"created_at">> => timestamp(Created),
      <<"updated_at">> => timestamp(Updated)}.

%% @doc Case-insensitive comparison used by the `?author=' list filter.
-spec matches_author(binary(), #book{}) -> boolean().
matches_author(Wanted, #book{author = Author}) ->
    string:equal(Wanted, Author, _IgnoreCase = true).

%%%===================================================================
%%% Field validators
%%%===================================================================

text(Field, Body, required) ->
    case maps:find(Field, Body) of
        error ->
            {error, err(Field, <<"is required">>)};
        {ok, Value} when is_binary(Value) ->
            case string:trim(Value) of
                <<>> ->
                    {error, err(Field, <<"must not be blank">>)};
                Trimmed when byte_size(Trimmed) > ?MAX_TEXT_LEN ->
                    {error, err(Field, too_long(?MAX_TEXT_LEN))};
                Trimmed ->
                    {ok, Trimmed}
            end;
        {ok, _Other} ->
            {error, err(Field, <<"must be a string">>)}
    end.

year(Body) ->
    case maps:get(<<"year">>, Body, null) of
        null ->
            {ok, null};
        Value when is_integer(Value), Value >= ?MIN_YEAR, Value =< ?MAX_YEAR ->
            {ok, Value};
        Value when is_integer(Value) ->
            {error, err(<<"year">>, <<"must be between -3000 and 2999">>)};
        _Other ->
            {error, err(<<"year">>, <<"must be an integer or null">>)}
    end.

isbn(Body) ->
    case maps:get(<<"isbn">>, Body, null) of
        null ->
            {ok, null};
        Value when is_binary(Value) ->
            case string:trim(Value) of
                <<>> -> {ok, null};
                Trimmed -> checked_isbn(Trimmed)
            end;
        _Other ->
            {error, err(<<"isbn">>, <<"must be a string or null">>)}
    end.

%% Structural check only (length + alphabet); no checksum is enforced so
%% that placeholder identifiers used during data entry still round-trip.
checked_isbn(Isbn) ->
    Digits = binary:replace(Isbn, [<<"-">>, <<" ">>], <<>>, [global]),
    case valid_isbn_digits(Digits) of
        true  -> {ok, Isbn};
        false -> {error, err(<<"isbn">>, <<"must be a valid ISBN-10 or ISBN-13">>)}
    end.

valid_isbn_digits(Digits) when byte_size(Digits) =:= 10 ->
    {Body, Check} = split_last(Digits),
    all_digits(Body) andalso (all_digits(Check) orelse Check =:= <<"X">>
                              orelse Check =:= <<"x">>);
valid_isbn_digits(Digits) when byte_size(Digits) =:= 13 ->
    all_digits(Digits);
valid_isbn_digits(_Digits) ->
    false.

split_last(Bin) ->
    N = byte_size(Bin) - 1,
    <<Body:N/binary, Last/binary>> = Bin,
    {Body, Last}.

all_digits(<<>>) -> true;
all_digits(<<C, Rest/binary>>) when C >= $0, C =< $9 -> all_digits(Rest);
all_digits(_) -> false.

%%%===================================================================
%%% Helpers
%%%===================================================================

err(Field, Message) ->
    #{<<"field">> => Field, <<"message">> => Message}.

too_long(Max) ->
    iolist_to_binary(io_lib:format("must be at most ~b bytes", [Max])).

timestamp(Seconds) when is_integer(Seconds) ->
    list_to_binary(
      calendar:system_time_to_rfc3339(Seconds, [{unit, second}, {offset, "Z"}])).
