%% CSV parser supporting quoted fields, BOM stripping, and multiple line endings.
-module(soccer_csv).
-export([parse_file/1]).

parse_file(Filename) ->
    case file:read_file(Filename) of
        {ok, Data} ->
            Clean = strip_bom(Data),
            Rows = parse_all_rows(Clean),
            NonEmpty = [R || R <- Rows, R =/= [<<>>], R =/= []],
            case NonEmpty of
                [] -> [];
                [Header | DataRows] ->
                    HdrLen = length(Header),
                    [maps:from_list(lists:zip(Header, Row))
                     || Row <- DataRows, length(Row) =:= HdrLen]
            end;
        {error, Reason} ->
            error({file_error, Filename, Reason})
    end.

strip_bom(<<239, 187, 191, Rest/binary>>) -> Rest;
strip_bom(Data) -> Data.

parse_all_rows(Data) ->
    parse_all_rows(Data, [], []).

parse_all_rows(<<>>, Row, Rows) ->
    case Row of
        [] -> lists:reverse(Rows);
        _ -> lists:reverse([lists:reverse(Row) | Rows])
    end;
parse_all_rows(Data, Row, Rows) ->
    {Field, Rest} = parse_field(Data),
    case Rest of
        <<",", Rest2/binary>> ->
            parse_all_rows(Rest2, [Field | Row], Rows);
        <<"\r\n", Rest2/binary>> ->
            FinRow = lists:reverse([Field | Row]),
            parse_all_rows(Rest2, [], [FinRow | Rows]);
        <<"\n", Rest2/binary>> ->
            FinRow = lists:reverse([Field | Row]),
            parse_all_rows(Rest2, [], [FinRow | Rows]);
        <<>> ->
            FinRow = lists:reverse([Field | Row]),
            lists:reverse([FinRow | Rows])
    end.

parse_field(<<"\"", Rest/binary>>) ->
    parse_quoted_field(Rest, []);
parse_field(Data) ->
    parse_normal_field(Data, []).

parse_normal_field(<<>> = Rest, Acc) ->
    {list_to_binary(lists:reverse(Acc)), Rest};
parse_normal_field(<<",", _/binary>> = Rest, Acc) ->
    {list_to_binary(lists:reverse(Acc)), Rest};
parse_normal_field(<<"\r\n", _/binary>> = Rest, Acc) ->
    {list_to_binary(lists:reverse(Acc)), Rest};
parse_normal_field(<<"\n", _/binary>> = Rest, Acc) ->
    {list_to_binary(lists:reverse(Acc)), Rest};
parse_normal_field(<<Byte, Rest/binary>>, Acc) ->
    parse_normal_field(Rest, [Byte | Acc]).

parse_quoted_field(<<>>, Acc) ->
    {list_to_binary(lists:reverse(Acc)), <<>>};
parse_quoted_field(<<"\"\"", Rest/binary>>, Acc) ->
    parse_quoted_field(Rest, [$" | Acc]);
parse_quoted_field(<<"\"", Rest/binary>>, Acc) ->
    {list_to_binary(lists:reverse(Acc)), Rest};
parse_quoted_field(<<Byte, Rest/binary>>, Acc) ->
    parse_quoted_field(Rest, [Byte | Acc]).
