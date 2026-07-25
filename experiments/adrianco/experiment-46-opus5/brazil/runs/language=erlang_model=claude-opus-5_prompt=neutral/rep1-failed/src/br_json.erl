%%%-------------------------------------------------------------------
%%% @doc JSON encoding/decoding on top of OTP's `json' module.
%%%
%%% Query results use atom keys and `undefined'/atom values, neither of
%%% which JSON has; {@link encode/1} normalises them (atom keys become
%%% strings, `undefined' becomes `null') so the rest of the code can
%%% stay idiomatic Erlang.
%%% @end
%%%-------------------------------------------------------------------
-module(br_json).

-export([encode/1, decode/1, sanitize/1]).

%%--------------------------------------------------------------------
%% @doc Encode any query result as a JSON binary.
-spec encode(term()) -> binary().
encode(Term) -> iolist_to_binary(json:encode(sanitize(Term))).

%%--------------------------------------------------------------------
%% @doc Decode a JSON binary; objects become maps with binary keys.
-spec decode(binary()) -> {ok, term()} | {error, term()}.
decode(Bin) ->
    try {ok, json:decode(Bin)}
    catch
        error:Reason -> {error, Reason};
        Class:Reason -> {error, {Class, Reason}}
    end.

%%--------------------------------------------------------------------
%% @doc Make a term JSON friendly.
-spec sanitize(term()) -> term().
sanitize(Map) when is_map(Map) ->
    maps:fold(fun(K, V, Acc) -> Acc#{key(K) => sanitize(V)} end, #{}, Map);
sanitize([]) -> [];             % an empty list is an empty array, not ""
sanitize(List) when is_list(List) ->
    case io_lib:printable_unicode_list(List) of
        true -> unicode:characters_to_binary(List);
        false -> [sanitize(V) || V <- List]
    end;
sanitize(Bin) when is_binary(Bin) -> ensure_utf8(Bin);
sanitize(undefined) -> null;
sanitize(true) -> true;
sanitize(false) -> false;
sanitize(null) -> null;
sanitize(A) when is_atom(A) -> atom_to_binary(A, utf8);
sanitize(T) when is_tuple(T) -> [sanitize(V) || V <- tuple_to_list(T)];
sanitize(V) -> V.

%% JSON strings must be UTF-8.  Data that arrives as Latin-1 (a couple
%% of rows in the Kaggle exports) is converted rather than rejected.
ensure_utf8(Bin) ->
    case unicode:characters_to_binary(Bin, utf8, utf8) of
        Valid when is_binary(Valid) -> Valid;
        _ -> unicode:characters_to_binary(Bin, latin1, utf8)
    end.

key(K) when is_binary(K) -> ensure_utf8(K);
key(K) when is_atom(K) -> atom_to_binary(K, utf8);
key(K) when is_integer(K) -> integer_to_binary(K);
key(K) -> br_text:to_binary(K).
