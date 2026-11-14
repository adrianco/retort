%%% Minimal RFC-4180 style CSV parser working on UTF-8 binaries.
%%% Handles quoted fields, doubled quotes, CRLF, a leading BOM and quoted
%%% fields spanning several lines.
-module(brsoccer_csv).
-export([parse/1, parse_file/1, to_maps/1, fold/3, fold_file_maps/3]).

-spec parse_file(file:name_all()) -> {ok, [[binary()]]} | {error, term()}.
parse_file(Path) ->
    case file:read_file(Path) of
        {ok, Bin} -> {ok, parse(Bin)};
        Err -> Err
    end.

-spec parse(binary()) -> [[binary()]].
parse(Bin) ->
    lists:reverse(fold(fun(Row, Acc) -> [Row | Acc] end, [], Bin)).

%% Streaming variant: calls Fun(Row, Acc) for each row (header included)
%% without materialising the whole table.
-spec fold(fun(([binary()], A) -> A), A, binary()) -> A.
fold(Fun, Acc, <<16#EF, 16#BB, 16#BF, Rest/binary>>) -> fold(Fun, Acc, Rest);
fold(Fun, Acc, Bin) ->
    rows(binary:split(Bin, <<"\n">>, [global]), Fun, Acc).

%% Fold over the data rows of a file as maps keyed by the header names.
-spec fold_file_maps(file:name_all(), fun((#{binary() => binary()}, A) -> A), A) ->
          {ok, A} | {error, term()}.
fold_file_maps(Path, Fun, Acc0) ->
    case file:read_file(Path) of
        {ok, Bin} ->
            {_, Out} = fold(fun(Row, {undefined, A}) -> {Row, A};
                               (Row, {Header, A}) -> {Header, Fun(maps:from_list(zip(Header, Row)), A)}
                            end, {undefined, Acc0}, Bin),
            {ok, Out};
        Err -> Err
    end.

rows([], _Fun, Acc) -> Acc;
rows([L0 | Rest], Fun, Acc) ->
    L = strip_cr(L0),
    case L of
        <<>> -> rows(Rest, Fun, Acc);
        _ ->
            case binary:match(L, <<"\"">>) of
                nomatch -> rows(Rest, Fun, Fun(binary:split(L, <<",">>, [global]), Acc));
                _ -> quoted(L, Rest, Fun, Acc)
            end
    end.

quoted(L, Rest, Fun, Acc) ->
    case fields(L, <<>>, false, []) of
        {ok, Fields} -> rows(Rest, Fun, Fun(Fields, Acc));
        open when Rest =/= [] ->
            [Next | Rest1] = Rest,
            quoted(<<L/binary, "\n", (strip_cr(Next))/binary>>, Rest1, Fun, Acc);
        open ->
            %% unterminated quote at EOF: be lenient
            Fun(binary:split(L, <<",">>, [global]), Acc)
    end.

fields(<<>>, _Cur, true, _Acc) -> open;
fields(<<>>, Cur, false, Acc) -> {ok, lists:reverse([Cur | Acc])};
fields(<<$", $", R/binary>>, Cur, true, Acc) -> fields(R, <<Cur/binary, $">>, true, Acc);
fields(<<$", R/binary>>, Cur, InQ, Acc) -> fields(R, Cur, not InQ, Acc);
fields(<<$,, R/binary>>, Cur, false, Acc) -> fields(R, <<>>, false, [Cur | Acc]);
fields(<<C, R/binary>>, Cur, InQ, Acc) -> fields(R, <<Cur/binary, C>>, InQ, Acc).

strip_cr(<<>>) -> <<>>;
strip_cr(L) ->
    S = byte_size(L) - 1,
    case L of
        <<P:S/binary, $\r>> -> P;
        _ -> L
    end.

%% First row is the header; returns one map per data row keyed by header name.
-spec to_maps([[binary()]]) -> [#{binary() => binary()}].
to_maps([]) -> [];
to_maps([Header | Rows]) ->
    [maps:from_list(zip(Header, R)) || R <- Rows].

zip([H | T], [V | VT]) -> [{H, V} | zip(T, VT)];
zip(_, _) -> [].
