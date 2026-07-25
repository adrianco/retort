%% RFC-4180-style CSV parser: quoted fields, "" escapes, CR/LF line ends,
%% UTF-8 pass-through, leading BOM stripped. Returns rows as lists of binaries.
-module(bsmcp_csv).

-export([parse_file/1, parse_binary/1]).

-spec parse_file(file:name_all()) -> [[binary()]].
parse_file(Path) ->
    {ok, Bin} = file:read_file(Path),
    parse_binary(Bin).

-spec parse_binary(binary()) -> [[binary()]].
parse_binary(Bin) ->
    Rows = rows(strip_bom(Bin), [], [], []),
    [Row || Row <- Rows, Row =/= [<<>>]].

strip_bom(<<16#EF, 16#BB, 16#BF, Rest/binary>>) -> Rest;
strip_bom(Bin) -> Bin.

%% rows(Input, FieldAcc(reversed byte list), RowAcc(reversed), RowsAcc(reversed))
rows(<<>>, [], [], Rows) ->
    lists:reverse(Rows);
rows(<<>>, Field, Row, Rows) ->
    lists:reverse([end_row(Field, Row) | Rows]);
rows(<<$", Rest/binary>>, [], Row, Rows) ->
    quoted(Rest, [], Row, Rows);
rows(<<$,, Rest/binary>>, Field, Row, Rows) ->
    rows(Rest, [], [end_field(Field) | Row], Rows);
rows(<<$\r, $\n, Rest/binary>>, Field, Row, Rows) ->
    rows(Rest, [], [], [end_row(Field, Row) | Rows]);
rows(<<$\r, Rest/binary>>, Field, Row, Rows) ->
    rows(Rest, [], [], [end_row(Field, Row) | Rows]);
rows(<<$\n, Rest/binary>>, Field, Row, Rows) ->
    rows(Rest, [], [], [end_row(Field, Row) | Rows]);
rows(<<C, Rest/binary>>, Field, Row, Rows) ->
    rows(Rest, [C | Field], Row, Rows).

%% Inside a quoted field. A doubled quote is a literal quote; a single quote
%% returns to the unquoted state (any trailing chars are appended verbatim).
quoted(<<$", $", Rest/binary>>, Field, Row, Rows) ->
    quoted(Rest, [$" | Field], Row, Rows);
quoted(<<$", Rest/binary>>, Field, Row, Rows) ->
    rows(Rest, Field, Row, Rows);
quoted(<<C, Rest/binary>>, Field, Row, Rows) ->
    quoted(Rest, [C | Field], Row, Rows);
quoted(<<>>, Field, Row, Rows) ->
    %% Unterminated quote at EOF: treat accumulated content as the field.
    lists:reverse([end_row(Field, Row) | Rows]).

end_field(Field) ->
    list_to_binary(lists:reverse(Field)).

end_row(Field, Row) ->
    lists:reverse([end_field(Field) | Row]).
