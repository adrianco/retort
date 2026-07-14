%%% ===================================================================
%%% Brazilian Soccer MCP Server - CSV reader
%%%
%%% Context: A small, dependency-free RFC-4180 style CSV parser used to
%%% ingest the Kaggle datasets. It must cope with the quirks present in
%%% the provided files:
%%%   * fields quoted with double quotes that themselves contain commas
%%%     (e.g. the FIFA "Joined" column: "Jul 1, 2004"),
%%%   * escaped quotes inside quoted fields ("" -> "),
%%%   * a UTF-8 byte-order-mark at the start of fifa_data.csv,
%%%   * both LF and CRLF line endings.
%%%
%%% Files are parsed into a list of rows of UTF-8 binaries. `parse_file/1'
%%% returns {Header, Rows} where Header is the first line's fields and
%%% Rows are maps of column-name => value for convenient access.
%%% ===================================================================
-module(bsoccer_csv).

-export([parse_file/1, parse_binary/1, rows_as_maps/1]).

%% Parse a CSV file into {Header :: [binary()], Rows :: [#{binary() => binary()}]}.
-spec parse_file(file:filename_all()) ->
          {ok, {[binary()], [#{binary() => binary()}]}} | {error, term()}.
parse_file(Path) ->
    case file:read_file(Path) of
        {ok, Bin} ->
            {ok, rows_as_maps(parse_binary(Bin))};
        {error, Reason} ->
            {error, Reason}
    end.

%% Turn raw rows (list of list of fields) into {Header, [RowMap]}.
rows_as_maps([]) ->
    {[], []};
rows_as_maps([Header | DataRows]) ->
    Cols = Header,
    NCols = length(Cols),
    Maps = [row_to_map(Cols, NCols, Fields)
            || Fields <- DataRows, Fields =/= [<<>>]],
    {Cols, Maps}.

row_to_map(Cols, NCols, Fields) ->
    %% Pad/truncate defensively so a short row never crashes ingestion.
    Padded = pad(Fields, NCols),
    maps:from_list(lists:zip(Cols, Padded)).

pad(Fields, N) ->
    L = length(Fields),
    if
        L =:= N -> Fields;
        L > N   -> lists:sublist(Fields, N);
        true    -> Fields ++ lists:duplicate(N - L, <<>>)
    end.

%% Parse a whole CSV binary into a list of rows; each row is a list of
%% field binaries.
-spec parse_binary(binary()) -> [[binary()]].
parse_binary(Bin0) ->
    Bin = strip_bom(Bin0),
    parse_rows(Bin, [], [], [], normal).

strip_bom(<<239, 187, 191, Rest/binary>>) -> Rest;  %% UTF-8 BOM
strip_bom(Bin) -> Bin.

%% State machine over the byte stream.
%%  Acc      - completed rows (reversed)
%%  RowAcc   - fields of the current row (reversed)
%%  FieldAcc - bytes of the current field (reversed iolist)
%%  State    - normal | quoted
parse_rows(<<>>, Acc, RowAcc, FieldAcc, _State) ->
    finish(Acc, RowAcc, FieldAcc);
%% Quoted field handling
parse_rows(<<$", Rest/binary>>, Acc, RowAcc, FieldAcc, normal) ->
    parse_rows(Rest, Acc, RowAcc, FieldAcc, quoted);
parse_rows(<<$", $", Rest/binary>>, Acc, RowAcc, FieldAcc, quoted) ->
    parse_rows(Rest, Acc, RowAcc, [$" | FieldAcc], quoted);
parse_rows(<<$", Rest/binary>>, Acc, RowAcc, FieldAcc, quoted) ->
    parse_rows(Rest, Acc, RowAcc, FieldAcc, normal);
parse_rows(<<C, Rest/binary>>, Acc, RowAcc, FieldAcc, quoted) ->
    parse_rows(Rest, Acc, RowAcc, [C | FieldAcc], quoted);
%% Field / row separators in normal state
parse_rows(<<$,, Rest/binary>>, Acc, RowAcc, FieldAcc, normal) ->
    parse_rows(Rest, Acc, [field(FieldAcc) | RowAcc], [], normal);
parse_rows(<<$\r, $\n, Rest/binary>>, Acc, RowAcc, FieldAcc, normal) ->
    parse_rows(Rest, [lists:reverse([field(FieldAcc) | RowAcc]) | Acc], [], [], normal);
parse_rows(<<$\n, Rest/binary>>, Acc, RowAcc, FieldAcc, normal) ->
    parse_rows(Rest, [lists:reverse([field(FieldAcc) | RowAcc]) | Acc], [], [], normal);
parse_rows(<<$\r, Rest/binary>>, Acc, RowAcc, FieldAcc, normal) ->
    parse_rows(Rest, [lists:reverse([field(FieldAcc) | RowAcc]) | Acc], [], [], normal);
parse_rows(<<C, Rest/binary>>, Acc, RowAcc, FieldAcc, normal) ->
    parse_rows(Rest, Acc, RowAcc, [C | FieldAcc], normal).

finish(Acc, [], []) ->
    lists:reverse(Acc);
finish(Acc, RowAcc, FieldAcc) ->
    lists:reverse([lists:reverse([field(FieldAcc) | RowAcc]) | Acc]).

field(FieldAcc) ->
    list_to_binary(lists:reverse(FieldAcc)).
