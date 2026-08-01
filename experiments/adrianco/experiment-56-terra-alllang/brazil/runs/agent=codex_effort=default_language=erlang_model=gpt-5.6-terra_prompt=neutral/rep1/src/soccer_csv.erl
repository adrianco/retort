-module(soccer_csv).
-export([read/1, parse_line/1]).

%% RFC4180-style CSV reader.  Fields are returned as UTF-8 binaries.
read(File) ->
    case file:read_file(File) of
        {ok, Bin} ->
            Lines = binary:split(Bin, <<"\n">>, [global]),
            case [parse_line(trim_cr(L)) || L <- Lines, trim_cr(L) =/= <<>>] of
                [] -> {error, empty_file};
                [Header | Rows] -> {ok, Header, Rows}
            end;
        Error -> Error
    end.

trim_cr(Bin) ->
    case Bin of
        <<>> -> <<>>;
        _ -> case binary:last(Bin) of $\r -> binary:part(Bin, 0, byte_size(Bin)-1); _ -> Bin end
    end.

parse_line(Line) -> parse_line(Line, false, <<>>, []).
parse_line(<<>>, _Quoted, Field, Acc) -> lists:reverse([Field | Acc]);
parse_line(<<$", $", Rest/binary>>, true, Field, Acc) ->
    parse_line(Rest, true, <<Field/binary, $">>, Acc);
parse_line(<<$", Rest/binary>>, Quoted, Field, Acc) ->
    parse_line(Rest, not Quoted, Field, Acc);
parse_line(<<$,, Rest/binary>>, false, Field, Acc) ->
    parse_line(Rest, false, <<>>, [Field | Acc]);
parse_line(<<C/utf8, Rest/binary>>, Quoted, Field, Acc) ->
    parse_line(Rest, Quoted, <<Field/binary, C/utf8>>, Acc).
