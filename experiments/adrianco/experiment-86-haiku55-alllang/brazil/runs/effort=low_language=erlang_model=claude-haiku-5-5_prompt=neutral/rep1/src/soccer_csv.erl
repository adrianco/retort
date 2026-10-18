%% Context: minimal RFC 4180 CSV parser for the Kaggle files in data/kaggle.
%% Handles a UTF-8 BOM, CRLF/LF line endings, quoted fields with "" escapes,
%% and quoted fields that span lines. Works on raw bytes, so UTF-8 is preserved.
-module(soccer_csv).
-export([parse/1, parse_maps/1]).

-spec parse(binary()) -> [[binary()]].
parse(Bin) ->
    rows(strip_bom(Bin), [], [], []).

%% Returns one map per data row, keyed by the trimmed header names.
-spec parse_maps(binary()) -> [#{binary() => binary()}].
parse_maps(Bin) ->
    case parse(Bin) of
        [] ->
            [];
        [Header | Rows] ->
            Keys = [string:trim(K) || K <- Header],
            N = length(Keys),
            [maps:from_list(lists:zip(Keys, pad(Row, N))) || Row <- Rows]
    end.

strip_bom(<<16#EF, 16#BB, 16#BF, Rest/binary>>) -> Rest;
strip_bom(Bin) -> Bin.

pad(Row, N) when length(Row) >= N ->
    lists:sublist(Row, N);
pad(Row, N) ->
    Row ++ lists:duplicate(N - length(Row), <<>>).

%% rows(Input, ReversedFieldBytes, ReversedFields, ReversedRows)
rows(<<>>, [], [], Rows) ->
    lists:reverse(Rows);
rows(<<>>, Field, Row, Rows) ->
    lists:reverse([lists:reverse([field(Field) | Row]) | Rows]);
rows(<<$", Rest/binary>>, [], Row, Rows) ->
    quoted(Rest, [], Row, Rows);
rows(<<$,, Rest/binary>>, Field, Row, Rows) ->
    rows(Rest, [], [field(Field) | Row], Rows);
rows(<<$\r, $\n, Rest/binary>>, Field, Row, Rows) ->
    eol(Rest, Field, Row, Rows);
rows(<<$\n, Rest/binary>>, Field, Row, Rows) ->
    eol(Rest, Field, Row, Rows);
rows(<<C, Rest/binary>>, Field, Row, Rows) ->
    rows(Rest, [C | Field], Row, Rows).

quoted(<<$", $", Rest/binary>>, Field, Row, Rows) ->
    quoted(Rest, [$" | Field], Row, Rows);
quoted(<<$", Rest/binary>>, Field, Row, Rows) ->
    rows(Rest, Field, Row, Rows);
quoted(<<C, Rest/binary>>, Field, Row, Rows) ->
    quoted(Rest, [C | Field], Row, Rows);
quoted(<<>>, Field, Row, Rows) ->
    rows(<<>>, Field, Row, Rows).

%% Blank lines are skipped rather than producing empty rows.
eol(Rest, [], [], Rows) ->
    rows(Rest, [], [], Rows);
eol(Rest, Field, Row, Rows) ->
    rows(Rest, [], [], [lists:reverse([field(Field) | Row]) | Rows]).

field(Reversed) ->
    list_to_binary(lists:reverse(Reversed)).
