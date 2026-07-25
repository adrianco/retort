%%%-------------------------------------------------------------------
%%% @doc Text, number and date helpers shared by the loaders and queries.
%%%
%%% Context: the datasets are Brazilian Portuguese UTF-8 ("São Paulo",
%%% "Grêmio", "Avaí", "Náutico"), use three different date encodings
%%% (`2023-09-24', `2012-05-19 18:30:00', `29/03/2003') and encode
%%% missing numbers in three different ways (`NA', `-', empty).  They
%%% also write integers as floats (`1.0') in the extended-stats file.
%%%
%%% `normalize/1' produces the search key used everywhere for
%%% accent/case/punctuation insensitive matching:
%%%   "Atlético - MG"  -> <<"atletico mg">>
%%%   "A.b.c. - RN"    -> <<"abc rn">>   (single letter runs are merged)
%%%   "Xv de Piracicaba" -> <<"xv piracicaba">> (stop words dropped)
%%% @end
%%%-------------------------------------------------------------------
-module(bsmcp_text).

-export([fold_accents/1, lower/1, normalize/1, tokens/1, trim/1,
         to_int/1, to_number/1, contains/2,
         parse_date/1, parse_time/1, format_date/1, date_year/1,
         round2/1, pct/2, bin/1, join/2]).

-define(STOPWORDS, [<<"de">>, <<"do">>, <<"da">>, <<"dos">>, <<"das">>,
                    <<"e">>, <<"of">>, <<"the">>]).

%%====================================================================
%% Strings
%%====================================================================

%% @doc Replace accented latin characters by their ASCII base letter.
-spec fold_accents(binary() | string()) -> binary().
fold_accents(Bin) when is_binary(Bin) ->
    case is_ascii(Bin) of
        true ->
            Bin;   % fast path: most rows have no accented characters
        false ->
            Chars = case unicode:characters_to_list(Bin, utf8) of
                        L when is_list(L) -> L;
                        _ -> binary_to_list(Bin)  % invalid UTF-8: treat as latin1
                    end,
            fold_accents(Chars)
    end;
fold_accents(Chars) when is_list(Chars) ->
    unicode:characters_to_binary([fold_char(C) || C <- Chars], utf8, utf8).

is_ascii(<<C, Rest/binary>>) when C < 128 -> is_ascii(Rest);
is_ascii(<<>>) -> true;
is_ascii(_) -> false.

fold_char(C) when C >= $A, C =< $Z -> C;
fold_char(C) when C >= $a, C =< $z -> C;
fold_char(C) when C < 128 -> C;
fold_char(C) when C >= 16#C0, C =< 16#C5 -> $A;
fold_char(16#C6) -> "AE";
fold_char(16#C7) -> $C;
fold_char(C) when C >= 16#C8, C =< 16#CB -> $E;
fold_char(C) when C >= 16#CC, C =< 16#CF -> $I;
fold_char(16#D0) -> $D;
fold_char(16#D1) -> $N;
fold_char(C) when C >= 16#D2, C =< 16#D6 -> $O;
fold_char(16#D8) -> $O;
fold_char(C) when C >= 16#D9, C =< 16#DC -> $U;
fold_char(16#DD) -> $Y;
fold_char(16#DF) -> "ss";
fold_char(C) when C >= 16#E0, C =< 16#E5 -> $a;
fold_char(16#E6) -> "ae";
fold_char(16#E7) -> $c;
fold_char(C) when C >= 16#E8, C =< 16#EB -> $e;
fold_char(C) when C >= 16#EC, C =< 16#EF -> $i;
fold_char(16#F0) -> $d;
fold_char(16#F1) -> $n;
fold_char(C) when C >= 16#F2, C =< 16#F6 -> $o;
fold_char(16#F8) -> $o;
fold_char(C) when C >= 16#F9, C =< 16#FC -> $u;
fold_char(C) when C =:= 16#FD; C =:= 16#FF -> $y;
fold_char(C) when C >= 16#100, C =< 16#17F ->
    %% Latin Extended-A (Š, Ž, ć, ł ... common in FIFA player names)
    lists:nth(C - 16#FF, latin_extended_a());
fold_char(_) -> $\s.

%% 128 entries, one per code point from 16#100 to 16#17F.
latin_extended_a() ->
    "AaAaAa"          % 100-105
    "CcCcCcCc"        % 106-10D
    "DdDd"            % 10E-111
    "EeEeEeEeEe"      % 112-11B
    "GgGgGgGg"        % 11C-123
    "HhHh"            % 124-127
    "IiIiIiIiIi"      % 128-131
    "IiJjKkk"         % 132-138
    "LlLlLlLlLl"      % 139-142
    "NnNnNnnNn"       % 143-14B
    "OoOoOoOo"        % 14C-153
    "RrRrRr"          % 154-159
    "SsSsSsSs"        % 15A-161
    "TtTtTt"          % 162-167
    "UuUuUuUuUuUu"    % 168-173
    "WwYyY"           % 174-178
    "ZzZzZz"          % 179-17E
    "s".              % 17F

-spec lower(binary()) -> binary().
lower(Bin) -> << <<(lower_char(C))>> || <<C>> <= Bin >>.

lower_char(C) when C >= $A, C =< $Z -> C + 32;
lower_char(C) -> C.

%% @doc Canonical lookup key: ascii, lowercase, punctuation free.
-spec normalize(binary() | undefined) -> binary().
normalize(undefined) -> <<>>;
normalize(Bin) when is_binary(Bin) ->
    Ascii = lower(fold_accents(Bin)),
    Cleaned = << <<(keep(C))>> || <<C>> <= Ascii >>,
    Toks = [T || T <- binary:split(Cleaned, <<" ">>, [global, trim_all]),
                 not lists:member(T, ?STOPWORDS)],
    join(merge_initials(Toks), <<" ">>).

keep(C) when C >= $a, C =< $z -> C;
keep(C) when C >= $0, C =< $9 -> C;
keep(_) -> $\s.

%% "a b c" -> "abc" (handles A.B.C. / C. R. B. style abbreviations)
merge_initials(Toks) -> merge_initials(Toks, []).

merge_initials([], Acc) -> lists:reverse(Acc);
merge_initials([T | Rest], Acc) when byte_size(T) =:= 1 ->
    {Run, Rest1} = lists:splitwith(fun(X) -> byte_size(X) =:= 1 end, [T | Rest]),
    case length(Run) of
        1 -> merge_initials(Rest1, [T | Acc]);
        _ -> merge_initials(Rest1, [iolist_to_binary(Run) | Acc])
    end;
merge_initials([T | Rest], Acc) ->
    merge_initials(Rest, [T | Acc]).

-spec tokens(binary()) -> [binary()].
tokens(Bin) ->
    binary:split(normalize(Bin), <<" ">>, [global, trim_all]).

-spec trim(binary()) -> binary().
trim(Bin) -> string:trim(Bin, both, " \t\r\n\"").

%% @doc Case/accent insensitive substring test.
-spec contains(binary(), binary()) -> boolean().
contains(_Haystack, <<>>) -> true;
contains(Haystack, Needle) ->
    H = normalize(Haystack),
    N = normalize(Needle),
    N =/= <<>> andalso binary:match(H, N) =/= nomatch.

-spec join([binary()], binary()) -> binary().
join([], _Sep) -> <<>>;
join([H | T], Sep) ->
    iolist_to_binary([H | [[Sep, X] || X <- T]]).

-spec bin(term()) -> binary().
bin(B) when is_binary(B) -> B;
bin(L) when is_list(L) -> unicode:characters_to_binary(L, utf8, utf8);
bin(A) when is_atom(A) -> atom_to_binary(A, utf8);
bin(I) when is_integer(I) -> integer_to_binary(I);
bin(F) when is_float(F) -> float_to_binary(F, [{decimals, 2}, compact]).

%%====================================================================
%% Numbers
%%====================================================================

%% @doc Integer from a CSV cell; `NA', `-', `' and junk become undefined.
-spec to_int(binary() | undefined) -> integer() | undefined.
to_int(undefined) -> undefined;
to_int(Bin) ->
    case to_number(Bin) of
        undefined -> undefined;
        N when is_integer(N) -> N;
        F when is_float(F) -> round(F)
    end.

-spec to_number(binary() | undefined) -> number() | undefined.
to_number(undefined) -> undefined;
to_number(Bin) when is_binary(Bin) ->
    %% Fast path for the clean "12" / "1.0" cells that make up ~99% of
    %% the ~1M numeric cells in the player file.
    case num(Bin) of
        {ok, N} -> N;
        error -> to_number_slow(Bin)
    end.

num(<<$-, Rest/binary>>) when Rest =/= <<>> ->
    case digits(Rest, none) of
        {ok, N} -> {ok, -N};
        error -> error
    end;
num(Bin) ->
    digits(Bin, none).

digits(<<D, Rest/binary>>, Acc) when D >= $0, D =< $9 ->
    digits(Rest, case Acc of none -> D - $0; _ -> Acc * 10 + D - $0 end);
digits(<<$., Rest/binary>>, Acc) when Acc =/= none ->
    frac(Rest, 0.1, Acc * 1.0);
digits(<<>>, none) -> error;
digits(<<>>, Acc) -> {ok, Acc};
digits(_, _) -> error.

frac(<<D, Rest/binary>>, Scale, Acc) when D >= $0, D =< $9 ->
    frac(Rest, Scale / 10, Acc + (D - $0) * Scale);
frac(<<>>, _Scale, Acc) -> {ok, Acc};
frac(_, _, _) -> error.

to_number_slow(Bin0) when is_binary(Bin0) ->
    Bin = string:trim(Bin0),
    case Bin of
        <<>> -> undefined;
        <<"NA">> -> undefined;
        <<"na">> -> undefined;
        <<"N/A">> -> undefined;
        <<"-">> -> undefined;
        <<"NaN">> -> undefined;
        _ ->
            case string:to_float(Bin) of
                {Float, <<>>} ->
                    Float;
                _ ->
                    case string:to_integer(Bin) of
                        {Int, <<>>} -> Int;
                        _ -> undefined
                    end
            end
    end.

-spec round2(number()) -> float().
round2(N) when is_number(N) -> erlang:round(N * 100) / 100.

-spec pct(number(), number()) -> float().
pct(_Part, 0) -> 0.0;
pct(Part, Total) -> round2(Part * 100 / Total).

%%====================================================================
%% Dates
%%====================================================================

%% @doc Accepts `YYYY-MM-DD[ HH:MM:SS]' and `DD/MM/YYYY'.
-spec parse_date(binary() | undefined) -> calendar:date() | undefined.
parse_date(undefined) -> undefined;
parse_date(Bin0) ->
    case string:trim(Bin0) of
        <<Y:4/binary, "-", M:2/binary, "-", D:2/binary, _/binary>> ->
            mk_date(Y, M, D);
        <<D:2/binary, "/", M:2/binary, "/", Y:4/binary, _/binary>> ->
            mk_date(Y, M, D);
        <<D:1/binary, "/", M:2/binary, "/", Y:4/binary, _/binary>> ->
            mk_date(Y, M, D);
        _ ->
            undefined
    end.

mk_date(Y, M, D) ->
    try
        Date = {binary_to_integer(Y), binary_to_integer(M), binary_to_integer(D)},
        case calendar:valid_date(Date) of
            true -> Date;
            false -> undefined
        end
    catch _:_ -> undefined
    end.

-spec parse_time(binary() | undefined) -> binary() | undefined.
parse_time(undefined) -> undefined;
parse_time(Bin) ->
    case binary:split(string:trim(Bin), [<<" ">>, <<"T">>]) of
        [_, <<H:2/binary, ":", M:2/binary, _/binary>>] -> <<H/binary, ":", M/binary>>;
        [<<H:2/binary, ":", M:2/binary, _/binary>>] -> <<H/binary, ":", M/binary>>;
        _ -> undefined
    end.

-spec format_date(calendar:date() | undefined) -> binary() | undefined.
format_date(undefined) -> undefined;
format_date({Y, M, D}) ->
    iolist_to_binary(io_lib:format("~4..0b-~2..0b-~2..0b", [Y, M, D])).

-spec date_year(calendar:date() | undefined) -> integer() | undefined.
date_year(undefined) -> undefined;
date_year({Y, _, _}) -> Y.
