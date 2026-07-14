-module(bsm_csv).
-export([parse_file/1, parse_file/2]).

parse_file(Path) ->
    parse_file(Path, #{}).

parse_file(Path, _Opts) ->
    {ok, Bin} = file:read_file(Path),
    Data = case Bin of
        <<16#EF, 16#BB, 16#BF, Rest/binary>> -> Rest;
        _ -> Bin
    end,
    Lines = binary:split(Data, [<<"\r\n">>, <<"\n">>], [global]),
    NonEmpty = [L || L <- Lines, L =/= <<>>],
    case NonEmpty of
        [] -> [];
        [HeaderLine | DataLines] ->
            Headers = parse_row(HeaderLine),
            [row_to_map(Headers, parse_row(L)) || L <- DataLines]
    end.

row_to_map(Headers, Values) ->
    NH = length(Headers),
    NV = length(Values),
    PaddedValues = if
        NV >= NH -> lists:sublist(Values, NH);
        true -> Values ++ lists:duplicate(NH - NV, <<>>)
    end,
    maps:from_list(lists:zip(Headers, PaddedValues)).

parse_row(Line) ->
    Fields = parse_fields(Line, [], [], false),
    lists:reverse(Fields).

%% parse_fields(Bin, Fields, CurrentChars, InQuote) -> Fields
parse_fields(<<>>, Fields, Current, _InQuote) ->
    [list_to_binary(lists:reverse(Current)) | Fields];
parse_fields(<<$", Rest/binary>>, Fields, Current, false) ->
    parse_fields(Rest, Fields, Current, true);
parse_fields(<<$", $", Rest/binary>>, Fields, Current, true) ->
    parse_fields(Rest, Fields, [$" | Current], true);
parse_fields(<<$", Rest/binary>>, Fields, Current, true) ->
    parse_fields(Rest, Fields, Current, false);
parse_fields(<<$,, Rest/binary>>, Fields, Current, false) ->
    Field = list_to_binary(lists:reverse(Current)),
    parse_fields(Rest, [Field | Fields], [], false);
parse_fields(<<Ch, Rest/binary>>, Fields, Current, InQuote) ->
    parse_fields(Rest, Fields, [Ch | Current], InQuote).
