%%%-------------------------------------------------------------------
%%% @doc JSON codec built on the OTP `json' module (OTP 27+), so the
%%% server has no external dependencies.
%%%
%%% Context: query results are plain maps with atom keys and may contain
%%% `undefined' (a missing score, an unknown date) or `{Y,M,D}' tuples.
%%% `encode/1' therefore sanitises the term first: `undefined' becomes
%%% JSON `null' and dates become ISO strings, because the raw encoder
%%% would render the atom as the string "undefined" and reject tuples.
%%% @end
%%%-------------------------------------------------------------------
-module(bsmcp_json).

-export([encode/1, decode/1, sanitize/1]).

-spec encode(term()) -> binary().
encode(Term) ->
    iolist_to_binary(json:encode(sanitize(Term))).

-spec decode(binary()) -> {ok, term()} | {error, term()}.
decode(Bin) ->
    try
        {ok, json:decode(Bin)}
    catch
        _:Reason -> {error, Reason}
    end.

-spec sanitize(term()) -> term().
sanitize(undefined) -> null;
sanitize(Map) when is_map(Map) ->
    maps:from_list([{sanitize_key(K), sanitize(V)} || {K, V} <- maps:to_list(Map)]);
sanitize({Y, M, D}) when is_integer(Y), is_integer(M), is_integer(D) ->
    bsmcp_text:format_date({Y, M, D});
sanitize(Tuple) when is_tuple(Tuple) ->
    [sanitize(X) || X <- tuple_to_list(Tuple)];
sanitize(List) when is_list(List) ->
    [sanitize(X) || X <- List];
sanitize(Other) ->
    Other.

sanitize_key(K) when is_atom(K) -> K;
sanitize_key(K) when is_binary(K) -> K;
sanitize_key(K) -> bsmcp_text:bin(K).
