%% Context: text helpers shared by the loader and the queries. Normalizes
%% Brazilian team names (state suffixes, parenthetical notes), tokenizes names
%% for accent- and case-insensitive matching, and parses the date and number
%% formats found in the CSV files.
-module(soccer_util).
-export([team_name/1, tokens/1, parse_date/1, format_date/1,
         parse_number/1, trim/1]).

%% "Palmeiras-SP" -> "Palmeiras"; "Boavista Sport Club (antigo X) - RJ" -> "Boavista Sport Club".
-spec team_name(binary()) -> binary().
team_name(Raw) ->
    NoParens = re:replace(Raw, <<"\\s*\\([^)]*\\)">>, <<>>, [global, unicode, {return, binary}]),
    NoState = re:replace(NoParens, <<"\\s*-\\s*[A-Z]{2,3}\\s*$">>, <<>>, [unicode, {return, binary}]),
    trim(NoState).

%% Lowercased ASCII word tokens with accents folded: "São Paulo" -> [<<"sao">>, <<"paulo">>].
-spec tokens(binary()) -> [binary()].
tokens(Bin) ->
    Chars = string:lowercase(unicode:characters_to_list(Bin)),
    Clean = [clean(fold(C)) || C <- Chars],
    [unicode:characters_to_binary(W) || W <- string:lexemes(Clean, " ")].

clean(C) when C >= $a, C =< $z -> C;
clean(C) when C >= $0, C =< $9 -> C;
clean(_) -> $\s.

fold(C) when C < 128 -> C;
fold(C) -> maps:get(C, accent_map(), C).

accent_map() ->
    maps:from_list([{X, Base}
                    || {Set, Base} <- [{"àáâãäå", $a}, {"ç", $c}, {"èéêë", $e},
                                       {"ìíîï", $i}, {"ñ", $n}, {"òóôõö", $o},
                                       {"ùúûü", $u}, {"ýÿ", $y}],
                       X <- unicode:characters_to_list(Set)]).

%% Accepts "2023-09-24", "2012-05-19 18:30:00" and "29/03/2003".
%% Returns {ok, YYYYMMDD} so dates compare as plain integers.
-spec parse_date(binary()) -> {ok, integer()} | error.
parse_date(Bin) ->
    case re:run(Bin, <<"^\\s*(\\d{4})-(\\d{1,2})-(\\d{1,2})">>, [{capture, all_but_first, binary}]) of
        {match, [Y, M, D]} ->
            ymd(Y, M, D);
        nomatch ->
            case re:run(Bin, <<"^\\s*(\\d{1,2})/(\\d{1,2})/(\\d{4})">>, [{capture, all_but_first, binary}]) of
                {match, [D, M, Y]} -> ymd(Y, M, D);
                nomatch -> error
            end
    end.

ymd(Y, M, D) ->
    Year = binary_to_integer(Y), Month = binary_to_integer(M), Day = binary_to_integer(D),
    case Month >= 1 andalso Month =< 12 andalso Day >= 1 andalso Day =< 31 of
        true -> {ok, Year * 10000 + Month * 100 + Day};
        false -> error
    end.

-spec format_date(integer()) -> binary().
format_date(YMD) ->
    iolist_to_binary(io_lib:format("~4..0B-~2..0B-~2..0B",
                                   [YMD div 10000, YMD div 100 rem 100, YMD rem 100])).

%% "2", "1.0" and "" (-> undefined) all parse; FIFA values like "€5M" do not.
-spec parse_number(binary()) -> integer() | undefined.
parse_number(Bin) ->
    T = trim(Bin),
    try
        binary_to_integer(T)
    catch
        error:badarg ->
            try trunc(binary_to_float(T))
            catch error:badarg -> undefined
            end
    end.

-spec trim(binary()) -> binary().
trim(Bin) ->
    unicode:characters_to_binary(string:trim(Bin)).
