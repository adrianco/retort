%% RFC 4180 style CSV parser working on UTF-8 binaries.
%% Handles quoted fields, doubled quotes, CRLF line endings and a leading BOM.
-module(bs_csv).
-export([parse/1, parse_maps/1]).

-spec parse(binary()) -> [[binary()]].
parse(<<16#EF, 16#BB, 16#BF, Rest/binary>>) -> parse(Rest);
parse(Bin) -> rows(Bin, [], []).

%% First row is the header; every other row becomes a map Header => Value.
%% Missing trailing columns are filled with <<>>.
-spec parse_maps(binary()) -> [#{binary() => binary()}].
parse_maps(Bin) ->
    case parse(Bin) of
        [] -> [];
        [Header | Rows] -> [maps:from_list(zip(Header, Row)) || Row <- Rows]
    end.

zip([H | Hs], [V | Vs]) -> [{H, V} | zip(Hs, Vs)];
zip([H | Hs], []) -> [{H, <<>>} | zip(Hs, [])];
zip([], _) -> [].

rows(<<>>, [], Acc) -> lists:reverse(Acc);
rows(Bin, Row, Acc) ->
    {Field, Rest, Term} = field(Bin),
    case Term of
        comma -> rows(Rest, [Field | Row], Acc);
        _ ->
            case lists:reverse([Field | Row]) of
                [<<>>] -> rows(Rest, [], Acc);
                Full -> rows(Rest, [], [Full | Acc])
            end
    end.

field(<<$", Rest/binary>>) -> quoted(Rest, <<>>);
field(Bin) ->
    case binary:match(Bin, [<<",">>, <<"\n">>]) of
        nomatch -> {strip_cr(Bin), <<>>, eof};
        {Pos, 1} ->
            <<F:Pos/binary, C, Rest/binary>> = Bin,
            case C of
                $, -> {F, Rest, comma};
                $\n -> {strip_cr(F), Rest, nl}
            end
    end.

quoted(<<$", $", Rest/binary>>, Acc) -> quoted(Rest, <<Acc/binary, $">>);
quoted(<<$", $,, Rest/binary>>, Acc) -> {Acc, Rest, comma};
quoted(<<$", $\r, $\n, Rest/binary>>, Acc) -> {Acc, Rest, nl};
quoted(<<$", $\n, Rest/binary>>, Acc) -> {Acc, Rest, nl};
quoted(<<$", Rest/binary>>, Acc) ->
    %% Closing quote followed by stray text: keep reading as unquoted.
    {More, Rest1, Term} = field(Rest),
    {<<Acc/binary, More/binary>>, Rest1, Term};
quoted(<<C, Rest/binary>>, Acc) -> quoted(Rest, <<Acc/binary, C>>);
quoted(<<>>, Acc) -> {Acc, <<>>, eof}.

strip_cr(<<>>) -> <<>>;
strip_cr(B) ->
    case binary:last(B) of
        $\r -> binary:part(B, 0, byte_size(B) - 1);
        _ -> B
    end.
