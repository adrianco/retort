%%%-------------------------------------------------------------------
%%% @doc A small RFC-4180 CSV reader.
%%%
%%% Handles quoted fields (including embedded commas, newlines and
%%% doubled quotes), CRLF line endings and a UTF-8 byte order mark -
%%% all of which occur in the supplied Kaggle exports.  Scanning is
%%% done with `binary:match/3' over the whole file so that fields are
%%% sub-binaries of the original data rather than freshly built lists.
%%% @end
%%%-------------------------------------------------------------------
-module(br_csv).

-export([parse/1,
         parse_file/1,
         fold_file/3,
         rows_to_maps/1]).

%% Delimiter patterns are compiled once per file: a 9 MB data set is
%% scanned about a million times and compiling on every call dominated
%% the load time.
-record(pat, {delims :: binary:cp(), quote :: binary:cp()}).

%%--------------------------------------------------------------------
%% @doc Parse CSV text into a list of rows, each a list of fields.
-spec parse(binary()) -> [[binary()]].
parse(Bin0) ->
    Bin = strip_bom(Bin0),
    Pat = #pat{delims = binary:compile_pattern([<<",">>, <<"\n">>]),
               quote = binary:compile_pattern(<<"\"">>)},
    lists:reverse(rows(Bin, 0, byte_size(Bin), [], [], Pat)).

%%--------------------------------------------------------------------
%% @doc Parse a file into `{Header, Rows}'.
-spec parse_file(file:name_all()) -> {ok, [binary()], [[binary()]]} | {error, term()}.
parse_file(Path) ->
    case file:read_file(Path) of
        {ok, Bin} ->
            case parse(Bin) of
                [] -> {error, empty_file};
                [Header | Rows] -> {ok, Header, Rows}
            end;
        {error, Reason} -> {error, Reason}
    end.

%%--------------------------------------------------------------------
%% @doc Fold over a CSV file, one map (header field => value) per row.
%%
%% Rows with fewer fields than the header are padded with `<<>>' and
%% surplus fields are ignored, so malformed lines never crash a load.
-spec fold_file(file:name_all(), fun((#{binary() => binary()}, Acc) -> Acc), Acc) ->
          {ok, Acc} | {error, term()}.
fold_file(Path, Fun, Acc0) ->
    case parse_file(Path) of
        {ok, Header, Rows} ->
            Keys = [normalise_key(K) || K <- Header],
            {ok, lists:foldl(fun(Row, Acc) -> Fun(zip(Keys, Row), Acc) end, Acc0, Rows)};
        {error, Reason} -> {error, Reason}
    end.

%%--------------------------------------------------------------------
%% @doc Convert `[Header | Rows]' into a list of maps.
-spec rows_to_maps([[binary()]]) -> [#{binary() => binary()}].
rows_to_maps([]) -> [];
rows_to_maps([Header | Rows]) ->
    Keys = [normalise_key(K) || K <- Header],
    [zip(Keys, Row) || Row <- Rows].

%%====================================================================
%% Internal
%%====================================================================

strip_bom(<<239, 187, 191, Rest/binary>>) -> Rest;
strip_bom(Bin) -> Bin.

normalise_key(K) -> string:trim(K).

zip(Keys, Row) -> zip(Keys, Row, #{}).

zip([], _, Acc) -> Acc;
zip([K | Ks], [], Acc) -> zip(Ks, [], Acc#{K => <<>>});
zip([K | Ks], [V | Vs], Acc) -> zip(Ks, Vs, Acc#{K => V}).

%% --- scanner -------------------------------------------------------
%% rows(Bin, Pos, Size, CurrentFields, CompletedRows)

rows(_Bin, Pos, Size, [], Acc, _Pat) when Pos >= Size ->
    Acc;
rows(_Bin, Pos, Size, Fields, Acc, _Pat) when Pos >= Size ->
    %% Reaching the end with fields pending means the input ended on a
    %% comma, so there is one final, empty field.
    [lists:reverse([<<>> | Fields]) | Acc];
rows(Bin, Pos, Size, Fields, Acc, Pat) ->
    {Field, NextPos, Terminator} = field(Bin, Pos, Size, Pat),
    case Terminator of
        comma -> rows(Bin, NextPos, Size, [Field | Fields], Acc, Pat);
        _ ->
            Row = lists:reverse([Field | Fields]),
            case Row of
                [<<>>] -> rows(Bin, NextPos, Size, [], Acc, Pat); % blank line
                _ -> rows(Bin, NextPos, Size, [], [Row | Acc], Pat)
            end
    end.

field(Bin, Pos, Size, Pat) ->
    case Bin of
        <<_:Pos/binary, $", _/binary>> -> quoted(Bin, Pos + 1, Size, [], Pat);
        _ -> plain(Bin, Pos, Size, Pat)
    end.

plain(Bin, Pos, Size, #pat{delims = Delims}) ->
    case binary:match(Bin, Delims, [{scope, {Pos, Size - Pos}}]) of
        nomatch ->
            {trim_cr(binary:part(Bin, Pos, Size - Pos)), Size, eof};
        {At, 1} ->
            Value = trim_cr(binary:part(Bin, Pos, At - Pos)),
            case binary:at(Bin, At) of
                $, -> {Value, At + 1, comma};
                $\n -> {Value, At + 1, newline}
            end
    end.

%% Inside a quoted field: find the next quote, treat "" as an escaped ".
quoted(Bin, Pos, Size, Parts, #pat{quote = Quote} = Pat) ->
    case binary:match(Bin, Quote, [{scope, {Pos, Size - Pos}}]) of
        nomatch ->
            {iolist_to_binary(lists:reverse([binary:part(Bin, Pos, Size - Pos) | Parts])),
             Size, eof};
        {At, 1} ->
            Chunk = binary:part(Bin, Pos, At - Pos),
            case Bin of
                <<_:(At + 1)/binary, $", _/binary>> ->
                    quoted(Bin, At + 2, Size, [<<"\"">>, Chunk | Parts], Pat);
                _ ->
                    Value = case Parts of
                                [] -> Chunk;
                                _ -> iolist_to_binary(lists:reverse([Chunk | Parts]))
                            end,
                    close(Bin, At + 1, Size, Value, Pat)
            end
    end.

%% After the closing quote: skip to the next delimiter.
close(_Bin, Pos, Size, Value, _Pat) when Pos >= Size ->
    {Value, Size, eof};
close(Bin, Pos, Size, Value, #pat{delims = Delims}) ->
    case binary:match(Bin, Delims, [{scope, {Pos, Size - Pos}}]) of
        nomatch -> {Value, Size, eof};
        {At, 1} ->
            case binary:at(Bin, At) of
                $, -> {Value, At + 1, comma};
                $\n -> {Value, At + 1, newline}
            end
    end.

trim_cr(<<>>) -> <<>>;
trim_cr(Bin) ->
    case binary:at(Bin, byte_size(Bin) - 1) of
        $\r -> binary:part(Bin, 0, byte_size(Bin) - 1);
        _ -> Bin
    end.
