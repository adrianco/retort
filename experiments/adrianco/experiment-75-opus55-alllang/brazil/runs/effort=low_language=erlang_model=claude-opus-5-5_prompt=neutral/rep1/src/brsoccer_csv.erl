%% Minimal RFC4180-style CSV parser (quoted fields, embedded commas/newlines, BOM).
-module(brsoccer_csv).
-export([parse_file/1, parse/1]).

%% Returns a list of maps keyed by header binaries.
parse_file(Path) ->
    {ok, Bin} = file:read_file(Path),
    parse(Bin).

parse(<<16#EF, 16#BB, 16#BF, Rest/binary>>) -> parse(Rest);
parse(Bin) ->
    case rows(Bin, [], [], <<>>) of
        [] -> [];
        [Header | Rows] ->
            H = [string:trim(F) || F <- Header],
            N = length(H),
            [maps:from_list(lists:zip(H, pad(R, N))) || R <- Rows, R =/= [<<>>]]
    end.

pad(R, N) when length(R) >= N -> lists:sublist(R, N);
pad(R, N) -> R ++ lists:duplicate(N - length(R), <<>>).

rows(<<>>, [], Rows, <<>>) -> lists:reverse(Rows);
rows(<<>>, Fields, Rows, Acc) -> lists:reverse([lists:reverse([Acc | Fields]) | Rows]);
rows(<<$", Rest/binary>>, Fields, Rows, <<>>) -> quoted(Rest, Fields, Rows, <<>>);
rows(<<$,, Rest/binary>>, Fields, Rows, Acc) -> rows(Rest, [Acc | Fields], Rows, <<>>);
rows(<<$\r, $\n, Rest/binary>>, Fields, Rows, Acc) -> endrow(Rest, Fields, Rows, Acc);
rows(<<$\n, Rest/binary>>, Fields, Rows, Acc) -> endrow(Rest, Fields, Rows, Acc);
rows(<<C, Rest/binary>>, Fields, Rows, Acc) -> rows(Rest, Fields, Rows, <<Acc/binary, C>>).

endrow(Rest, Fields, Rows, Acc) ->
    rows(Rest, [], [lists:reverse([Acc | Fields]) | Rows], <<>>).

quoted(<<$", $", Rest/binary>>, F, R, Acc) -> quoted(Rest, F, R, <<Acc/binary, $">>);
quoted(<<$", Rest/binary>>, F, R, Acc) -> rows(Rest, F, R, Acc);
quoted(<<C, Rest/binary>>, F, R, Acc) -> quoted(Rest, F, R, <<Acc/binary, C>>);
quoted(<<>>, F, R, Acc) -> rows(<<>>, F, R, Acc).
