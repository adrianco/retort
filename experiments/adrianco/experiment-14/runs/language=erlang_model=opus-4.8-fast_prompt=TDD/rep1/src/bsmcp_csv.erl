%% @doc Minimal RFC-4180-style CSV parser.
%%
%% Handles quoted fields (with embedded commas, newlines and escaped
%% `""' quotes), CRLF or LF line endings, a leading UTF-8 BOM and
%% preserves raw UTF-8 bytes in every field.
-module(bsmcp_csv).

-export([parse/1, parse_to_maps/1, parse_file/1, parse_file_to_maps/1]).

%% @doc Parse a CSV binary into a list of rows, each a list of binary fields.
-spec parse(binary()) -> [[binary()]].
parse(Bin0) ->
    Bin = strip_bom(Bin0),
    rows(Bin, [], [], <<>>, false).

%% @doc Parse a CSV binary using its first row as a header, returning one
%% map per data row keyed by the header field names.
-spec parse_to_maps(binary()) -> [map()].
parse_to_maps(Bin) ->
    case parse(Bin) of
        [] -> [];
        [Header | Rows] ->
            [row_to_map(Header, R) || R <- Rows, R =/= [<<>>]]
    end.

%% @doc Read and parse a file path into rows.
-spec parse_file(file:name_all()) -> [[binary()]].
parse_file(Path) ->
    {ok, Bin} = file:read_file(Path),
    parse(Bin).

%% @doc Read and parse a file path into header-keyed maps.
-spec parse_file_to_maps(file:name_all()) -> [map()].
parse_file_to_maps(Path) ->
    {ok, Bin} = file:read_file(Path),
    parse_to_maps(Bin).

%% --- internal ---------------------------------------------------------

strip_bom(<<239,187,191, Rest/binary>>) -> Rest;
strip_bom(Bin) -> Bin.

row_to_map(Header, Fields) ->
    maps:from_list(zip_pad(Header, Fields)).

%% Pair header names with field values, tolerating rows shorter/longer
%% than the header.
zip_pad([], _) -> [];
zip_pad([H | Hs], [F | Fs]) -> [{H, F} | zip_pad(Hs, Fs)];
zip_pad([H | Hs], []) -> [{H, <<>>} | zip_pad(Hs, [])].

%% rows(Remaining, AccRows, AccFields, CurField, InQuotes)
rows(<<>>, AccRows, AccFields, Cur, _InQ) ->
    finish(AccRows, AccFields, Cur);
%% inside a quoted field
rows(<<$", $", Rest/binary>>, AccRows, AccFields, Cur, true) ->
    rows(Rest, AccRows, AccFields, <<Cur/binary, $">>, true);
rows(<<$", Rest/binary>>, AccRows, AccFields, Cur, true) ->
    rows(Rest, AccRows, AccFields, Cur, false);
rows(<<C, Rest/binary>>, AccRows, AccFields, Cur, true) ->
    rows(Rest, AccRows, AccFields, <<Cur/binary, C>>, true);
%% outside quotes
rows(<<$", Rest/binary>>, AccRows, AccFields, Cur, false) ->
    rows(Rest, AccRows, AccFields, Cur, true);
rows(<<$,, Rest/binary>>, AccRows, AccFields, Cur, false) ->
    rows(Rest, AccRows, [Cur | AccFields], <<>>, false);
rows(<<$\r, $\n, Rest/binary>>, AccRows, AccFields, Cur, false) ->
    rows(Rest, [lists:reverse([Cur | AccFields]) | AccRows], [], <<>>, false);
rows(<<$\n, Rest/binary>>, AccRows, AccFields, Cur, false) ->
    rows(Rest, [lists:reverse([Cur | AccFields]) | AccRows], [], <<>>, false);
rows(<<$\r, Rest/binary>>, AccRows, AccFields, Cur, false) ->
    rows(Rest, [lists:reverse([Cur | AccFields]) | AccRows], [], <<>>, false);
rows(<<C, Rest/binary>>, AccRows, AccFields, Cur, false) ->
    rows(Rest, AccRows, AccFields, <<Cur/binary, C>>, false).

finish(AccRows, [], <<>>) ->
    %% File ended exactly on a row boundary: no dangling final row.
    lists:reverse(AccRows);
finish(AccRows, AccFields, Cur) ->
    lists:reverse([lists:reverse([Cur | AccFields]) | AccRows]).
