%%% =====================================================================
%%% bsoccer_csv — minimal RFC-4180 CSV reader for the soccer datasets.
%%%
%%% The Kaggle exports use comma-separated values where individual fields may
%%% be wrapped in double quotes (so they can themselves contain commas, e.g.
%%% the FIFA "Joined" column `"Jul 1, 2004"`). Quotes are escaped by doubling
%%% (`""`). None of the provided files contain newlines inside quoted fields
%%% (verified against the data), so we parse line-by-line which keeps the
%%% reader fast on the 9 MB FIFA file while still honouring quoted commas.
%%%
%%% Public API:
%%%   parse_file/1  -> {Header :: [binary()], Rows :: [[binary()]]}
%%%   parse/1       -> same, from an in-memory binary
%%%   rows_as_maps/2-> [#{ColumnName => Value}] using the header as keys
%%%
%%% All values are returned as UTF-8 binaries with surrounding quotes removed
%%% and leading/trailing whitespace preserved (callers trim where needed).
%%% =====================================================================
-module(bsoccer_csv).

-export([parse_file/1, parse/1, rows_as_maps/2, parse_file_as_maps/1]).

%% Read and parse a CSV file from disk.
-spec parse_file(file:name_all()) -> {[binary()], [[binary()]]}.
parse_file(Path) ->
    {ok, Bin} = file:read_file(Path),
    parse(Bin).

%% Parse a whole CSV document held in a binary.
-spec parse(binary()) -> {[binary()], [[binary()]]}.
parse(Bin0) ->
    Bin = strip_bom(Bin0),
    Lines = split_lines(Bin),
    case Lines of
        [] -> {[], []};
        [HeaderLine | DataLines] ->
            Header = split_fields(HeaderLine),
            Rows = [split_fields(L) || L <- DataLines, L =/= <<>>],
            {Header, Rows}
    end.

%% Convenience: read a file and return each row as a map keyed by column name.
-spec parse_file_as_maps(file:name_all()) -> [#{binary() => binary()}].
parse_file_as_maps(Path) ->
    {Header, Rows} = parse_file(Path),
    rows_as_maps(Header, Rows).

%% Zip a header with each row to produce column-name keyed maps. Short rows are
%% padded with empty binaries; extra trailing columns are ignored.
-spec rows_as_maps([binary()], [[binary()]]) -> [#{binary() => binary()}].
rows_as_maps(Header, Rows) ->
    [row_to_map(Header, R) || R <- Rows].

row_to_map(Header, Row) ->
    maps:from_list(zip_pad(Header, Row)).

zip_pad([], _) -> [];
zip_pad([H | HT], [V | VT]) -> [{H, V} | zip_pad(HT, VT)];
zip_pad([H | HT], []) -> [{H, <<>>} | zip_pad(HT, [])].

%% --- line splitting -------------------------------------------------------

strip_bom(<<239, 187, 191, Rest/binary>>) -> Rest;  %% UTF-8 BOM
strip_bom(Bin) -> Bin.

split_lines(Bin) ->
    %% Normalise CRLF/CR to LF then split.
    Norm = binary:replace(Bin, <<"\r\n">>, <<"\n">>, [global]),
    Norm2 = binary:replace(Norm, <<"\r">>, <<"\n">>, [global]),
    binary:split(Norm2, <<"\n">>, [global]).

%% --- field splitting (quote aware) ---------------------------------------

split_fields(Line) ->
    split_fields(Line, false, <<>>, []).

%% State machine over the bytes of a single line.
%%   InQuote :: boolean()  — are we inside a quoted field?
%%   Cur     :: binary()   — accumulated bytes of the current field
%%   Acc     :: [binary()] — completed fields, reversed
split_fields(<<>>, _InQuote, Cur, Acc) ->
    lists:reverse([Cur | Acc]);
split_fields(<<$", $", Rest/binary>>, true, Cur, Acc) ->
    %% Escaped quote inside a quoted field.
    split_fields(Rest, true, <<Cur/binary, $">>, Acc);
split_fields(<<$", Rest/binary>>, true, Cur, Acc) ->
    %% Closing quote.
    split_fields(Rest, false, Cur, Acc);
split_fields(<<$", Rest/binary>>, false, Cur, Acc) ->
    %% Opening quote (any text already accumulated is unusual but preserved).
    split_fields(Rest, true, Cur, Acc);
split_fields(<<$,, Rest/binary>>, false, Cur, Acc) ->
    %% Field separator outside quotes.
    split_fields(Rest, false, <<>>, [Cur | Acc]);
split_fields(<<C, Rest/binary>>, InQuote, Cur, Acc) ->
    split_fields(Rest, InQuote, <<Cur/binary, C>>, Acc).
