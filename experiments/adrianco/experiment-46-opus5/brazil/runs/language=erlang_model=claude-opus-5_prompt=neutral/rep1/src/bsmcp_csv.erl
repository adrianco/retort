%%%-------------------------------------------------------------------
%%% @doc RFC-4180 style CSV reader used to ingest the Kaggle datasets.
%%%
%%% Context: the six provided CSV files mix conventions - quoted and
%%% unquoted fields, embedded commas inside quotes (e.g. "Jul 1, 2004"),
%%% a UTF-8 BOM on `fifa_data.csv', CRLF line endings and rows that are
%%% shorter than the header.  Everything is parsed from binaries so the
%%% 9 MB player file stays cheap, and the parser is byte oriented which
%%% keeps UTF-8 sequences intact (accents are never split).
%%%
%%% A parsed file is returned as a `table()': the header list, a
%%% column-name -> position index and the data rows as tuples, so field
%%% access is O(1) without building one map per row.
%%% @end
%%%-------------------------------------------------------------------
-module(bsmcp_csv).

-export([parse/1, parse_file/1, field/3, rows/1, headers/1]).

-type table() :: #{headers := [binary()],
                   index := #{binary() => pos_integer()},
                   rows := [tuple()]}.
-export_type([table/0]).

%%====================================================================
%% API
%%====================================================================

-spec parse_file(file:name_all()) -> {ok, table()} | {error, term()}.
parse_file(Path) ->
    case file:read_file(Path) of
        {ok, Bin} -> {ok, parse(Bin)};
        {error, Reason} -> {error, {Reason, Path}}
    end.

-spec parse(binary()) -> table().
parse(Bin0) ->
    Bin = strip_bom(Bin0),
    case parse_rows(Bin, []) of
        [] ->
            #{headers => [], index => #{}, rows => []};
        [HeaderRow | DataRows] ->
            Headers = [bsmcp_text:trim(H) || H <- HeaderRow],
            Width = length(Headers),
            Index = build_index(Headers),
            #{headers => Headers,
              index => Index,
              rows => [pad(R, Width) || R <- DataRows]}
    end.

-spec headers(table()) -> [binary()].
headers(#{headers := H}) -> H.

-spec rows(table()) -> [tuple()].
rows(#{rows := R}) -> R.

%% @doc Value of column `Name' in `Row'; `<<>>' when the column is absent.
-spec field(tuple(), table(), binary()) -> binary().
field(Row, #{index := Index}, Name) ->
    case Index of
        #{Name := Pos} when Pos =< tuple_size(Row) -> element(Pos, Row);
        _ -> <<>>
    end.

%%====================================================================
%% Internals
%%====================================================================

build_index(Headers) ->
    {Index, _} =
        lists:foldl(fun(H, {Acc, Pos}) ->
                            %% first occurrence wins for duplicated headers
                            case maps:is_key(H, Acc) of
                                true -> {Acc, Pos + 1};
                                false -> {Acc#{H => Pos}, Pos + 1}
                            end
                    end, {#{}, 1}, Headers),
    Index.

pad(Fields, Width) ->
    N = length(Fields),
    Padded = if
                 N =:= Width -> Fields;
                 N < Width -> Fields ++ lists:duplicate(Width - N, <<>>);
                 true -> lists:sublist(Fields, Width)
             end,
    list_to_tuple(Padded).

strip_bom(<<239, 187, 191, Rest/binary>>) -> Rest;
strip_bom(Bin) -> Bin.

parse_rows(<<>>, Acc) ->
    lists:reverse(Acc);
parse_rows(Bin, Acc) ->
    {Row, Rest} = parse_row(Bin, []),
    case is_blank(Row) of
        true -> parse_rows(Rest, Acc);
        false -> parse_rows(Rest, [Row | Acc])
    end.

%% parse_row/2 always yields at least one field, so a blank line shows
%% up as a single empty field.
is_blank([<<>>]) -> true;
is_blank(_) -> false.

parse_row(Bin, Fields) ->
    {Field, Sep, Rest} = parse_field(Bin),
    Fields1 = [Field | Fields],
    case Sep of
        comma -> parse_row(Rest, Fields1);
        _ -> {lists:reverse(Fields1), Rest}
    end.

parse_field(<<$", Rest/binary>>) -> parse_quoted(Rest, []);
parse_field(Bin) -> parse_plain(Bin).

parse_plain(Bin) ->
    case binary:match(Bin, [<<",">>, <<"\n">>]) of
        nomatch ->
            {trim_cr(Bin), eof, <<>>};
        {Pos, 1} ->
            Value = trim_cr(binary:part(Bin, 0, Pos)),
            Rest = binary:part(Bin, Pos + 1, byte_size(Bin) - Pos - 1),
            case binary:at(Bin, Pos) of
                $, -> {Value, comma, Rest};
                _ -> {Value, newline, Rest}
            end
    end.

parse_quoted(Bin, Acc) ->
    case binary:match(Bin, <<$">>) of
        nomatch ->
            %% unterminated quote - take the remainder
            {finish([Bin | Acc]), eof, <<>>};
        {Pos, 1} ->
            Chunk = binary:part(Bin, 0, Pos),
            Rest = binary:part(Bin, Pos + 1, byte_size(Bin) - Pos - 1),
            case Rest of
                <<$", Rest1/binary>> ->
                    %% "" is an escaped quote inside the field
                    parse_quoted(Rest1, [<<$">>, Chunk | Acc]);
                <<$,, Rest1/binary>> ->
                    {finish([Chunk | Acc]), comma, Rest1};
                <<$\r, $\n, Rest1/binary>> ->
                    {finish([Chunk | Acc]), newline, Rest1};
                <<$\n, Rest1/binary>> ->
                    {finish([Chunk | Acc]), newline, Rest1};
                <<>> ->
                    {finish([Chunk | Acc]), eof, <<>>};
                _ ->
                    %% junk after the closing quote: append it verbatim
                    {Tail, Sep, Rest1} = parse_plain(Rest),
                    {finish([Tail, Chunk | Acc]), Sep, Rest1}
            end
    end.

finish(RevChunks) ->
    iolist_to_binary(lists:reverse(RevChunks)).

trim_cr(Bin) ->
    Size = byte_size(Bin),
    case Size > 0 andalso binary:at(Bin, Size - 1) =:= $\r of
        true -> binary:part(Bin, 0, Size - 1);
        false -> Bin
    end.
