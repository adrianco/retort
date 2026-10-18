%% @doc RFC 4180 CSV parsing over binaries. Handles quoted fields, doubled
%% quotes, embedded commas/newlines, CRLF line endings and a UTF-8 BOM.
-module(bsm_csv).
-export([parse/1, rows_as_maps/1]).

-spec parse(binary()) -> [[binary()]].
parse(Bin) ->
    lists:reverse(rows(strip_bom(Bin), [])).

%% @doc Rows keyed by the header line. Rows whose width differs from the
%% header are dropped rather than crashing the whole load.
-spec rows_as_maps(binary()) -> [#{binary() => binary()}].
rows_as_maps(Bin) ->
    case parse(Bin) of
        [] -> [];
        [Header | Rows] ->
            Keys = [bsm_text:trim(H) || H <- Header],
            [maps:from_list(lists:zip(Keys, Row))
             || Row <- Rows, length(Row) =:= length(Keys)]
    end.

strip_bom(<<16#EF, 16#BB, 16#BF, Rest/binary>>) -> Rest;
strip_bom(Bin) -> Bin.

rows(<<>>, Acc) ->
    Acc;
rows(Bin, Acc) ->
    {Fields, Rest} = row(Bin, []),
    %% Blank lines come back as a single empty field; skip them.
    rows(Rest, case Fields of
                   [<<>>] -> Acc;
                   _ -> [lists:reverse(Fields) | Acc]
               end).

row(Bin, Fields) ->
    {Field, Rest} = field(Bin),
    case Rest of
        <<$,, R/binary>> -> row(R, [Field | Fields]);
        <<"\r\n", R/binary>> -> {[Field | Fields], R};
        <<$\n, R/binary>> -> {[Field | Fields], R};
        <<$\r, R/binary>> -> {[Field | Fields], R};
        <<>> -> {[Field | Fields], <<>>}
    end.

field(<<$", Bin/binary>>) ->
    quoted(Bin, []);
field(Bin) ->
    case binary:match(Bin, [<<",">>, <<"\n">>, <<"\r">>]) of
        {Pos, _} -> {binary:part(Bin, 0, Pos), binary:part(Bin, Pos, byte_size(Bin) - Pos)};
        nomatch -> {Bin, <<>>}
    end.

quoted(Bin, Acc) ->
    case binary:split(Bin, <<$">>) of
        [Before, <<$", Rest/binary>>] -> quoted(Rest, [<<$">>, Before | Acc]);
        [Before, Rest] -> {iolist_to_binary(lists:reverse([Before | Acc])), Rest};
        [Before] -> {iolist_to_binary(lists:reverse([Before | Acc])), <<>>}
    end.
