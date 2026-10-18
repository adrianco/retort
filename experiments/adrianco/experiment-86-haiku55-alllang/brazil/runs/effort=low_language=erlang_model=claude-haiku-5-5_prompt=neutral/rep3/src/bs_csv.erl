%%% Minimal RFC 4180 CSV parser working on UTF-8 binaries.
%%%
%%% Handles quoted fields (including embedded commas and doubled quotes),
%%% CRLF or LF line endings, a leading UTF-8 byte-order mark and blank lines.
%%% Delimiters are ASCII, so they can be found byte-wise without breaking
%%% multi-byte UTF-8 sequences.
-module(bs_csv).

-export([parse/1, read_file/1, read_maps/1]).

-spec parse(binary()) -> [[binary()]].
parse(Bin) ->
    rows(strip_bom(Bin), [], []).

%% Reads a file and returns one map per data row, keyed by header name.
-spec read_maps(file:filename_all()) -> [#{binary() => binary()}].
read_maps(Path) ->
    [Header | Rows] = parse(read_file(Path)),
    [maps:from_list(zip(Header, Row)) || Row <- Rows].

-spec read_file(file:filename_all()) -> binary().
read_file(Path) ->
    {ok, Bin} = file:read_file(Path),
    Bin.

%% --- internals -------------------------------------------------------------

strip_bom(<<16#EF, 16#BB, 16#BF, Rest/binary>>) -> Rest;
strip_bom(Bin) -> Bin.

rows(<<>>, [], Acc) ->
    lists:reverse(Acc);
rows(Bin, Row, Acc) ->
    {Field, Rest} = field(Bin),
    case Rest of
        <<$,, More/binary>> ->
            rows(More, [Field | Row], Acc);
        <<$\r, $\n, More/binary>> ->
            rows(More, [], add_row(Field, Row, Acc));
        <<$\n, More/binary>> ->
            rows(More, [], add_row(Field, Row, Acc));
        <<>> ->
            lists:reverse(add_row(Field, Row, Acc))
    end.

%% Skip blank lines, which parse as a single empty field.
add_row(<<>>, [], Acc) -> Acc;
add_row(Field, Row, Acc) -> [lists:reverse([Field | Row]) | Acc].

field(<<$", Rest/binary>>) -> quoted(Rest, []);
field(Bin) ->
    Len = plain_len(Bin, 0),
    <<Field:Len/binary, Rest/binary>> = Bin,
    {Field, Rest}.

plain_len(<<C, _/binary>>, N) when C =:= $,; C =:= $\n; C =:= $\r -> N;
plain_len(<<_, Rest/binary>>, N) -> plain_len(Rest, N + 1);
plain_len(<<>>, N) -> N.

quoted(Bin, Acc) ->
    case binary:match(Bin, <<$">>) of
        nomatch ->
            {iolist_to_binary([Acc, Bin]), <<>>};
        {Pos, 1} ->
            <<Part:Pos/binary, $", Rest/binary>> = Bin,
            Acc1 = [Acc, Part],
            case Rest of
                <<$", More/binary>> -> quoted(More, [Acc1, $"]);
                _ -> {iolist_to_binary(Acc1), Rest}
            end
    end.

zip([K | Ks], [V | Vs]) -> [{K, V} | zip(Ks, Vs)];
zip(_, _) -> [].
