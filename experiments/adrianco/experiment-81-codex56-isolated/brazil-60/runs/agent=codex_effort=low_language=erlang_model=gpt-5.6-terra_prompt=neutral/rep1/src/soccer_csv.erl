-module(soccer_csv).
-export([read/1, parse_line/1]).

read(Path) ->
    case file:read_file(Path) of
        {ok, Bin} ->
            Lines = [L || L <- binary:split(Bin, <<"\n">>, [global]), L =/= <<>>],
            case Lines of
                [] -> {ok, []};
                [Header | Rows] ->
                    Keys = [clean(K) || K <- parse_line(Header)],
                    {ok, [maps:from_list(lists:zip(Keys, [clean(V) || V <- parse_line(R)])) || R <- Rows]}
            end;
        Error -> Error
    end.

parse_line(Bin) when is_binary(Bin) -> parse_line(binary_to_list(Bin), false, [], []).
parse_line([], _Quoted, Field, Acc) -> lists:reverse([list_to_binary(lists:reverse(Field)) | Acc]);
parse_line([$" , $" | Rest], true, Field, Acc) -> parse_line(Rest, true, [$" | Field], Acc);
parse_line([$" | Rest], Quoted, Field, Acc) -> parse_line(Rest, not Quoted, Field, Acc);
parse_line([$, | Rest], false, Field, Acc) -> parse_line(Rest, false, [], [list_to_binary(lists:reverse(Field)) | Acc]);
parse_line([C | Rest], Quoted, Field, Acc) -> parse_line(Rest, Quoted, [C | Field], Acc).

clean(<<239,187,191, Rest/binary>>) -> clean(Rest);
clean(Bin) -> list_to_binary(string:trim(binary_to_list(Bin), trailing, "\r")).
