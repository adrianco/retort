-module(soccer_csv).
-export([read/1, parse_line/1]).

read(Path) ->
    {ok, Bin} = file:read_file(Path),
    Lines = string:split(unicode:characters_to_list(Bin), "\n", all),
    [parse_line(string:trim(Line, trailing, "\r")) || Line <- Lines, string:trim(Line) =/= ""].

%% RFC-4180-style fields, including commas and escaped quotes.
parse_line(Line) -> parse_line(Line, false, [], []).
parse_line([], _Quoted, Field, Fields) -> lists:reverse([lists:reverse(Field) | Fields]);
parse_line([$", $" | Rest], true, Field, Fields) -> parse_line(Rest, true, [$" | Field], Fields);
parse_line([$" | Rest], Quoted, Field, Fields) -> parse_line(Rest, not Quoted, Field, Fields);
parse_line([$, | Rest], false, Field, Fields) -> parse_line(Rest, false, [], [lists:reverse(Field) | Fields]);
parse_line([C | Rest], Quoted, Field, Fields) -> parse_line(Rest, Quoted, [C | Field], Fields).
