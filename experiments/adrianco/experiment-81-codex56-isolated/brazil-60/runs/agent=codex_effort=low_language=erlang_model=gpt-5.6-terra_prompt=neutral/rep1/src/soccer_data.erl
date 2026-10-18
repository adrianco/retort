-module(soccer_data).
-compile({encoding, utf8}).
-export([load/0, load/1, matches/1, players/1, normalize_team/1, parse_date/1]).

load() -> load("data/kaggle").
load(Directory) ->
    MatchFiles = [{"Brasileirao_Matches.csv", <<"Brasileirao">>, brasileirao},
                  {"Brazilian_Cup_Matches.csv", <<"Copa do Brasil">>, cup},
                  {"Libertadores_Matches.csv", <<"Libertadores">>, libertadores},
                  {"BR-Football-Dataset.csv", <<"Extended Statistics">>, extended},
                  {"novo_campeonato_brasileiro.csv", <<"Brasileirao Historical">>, historical}],
    try
        Ms = lists:append([load_matches(filename:join(Directory, F), C, Kind) || {F,C,Kind} <- MatchFiles]),
        {ok, Ps} = soccer_csv:read(filename:join(Directory, "fifa_data.csv")),
        {ok, #{matches => Ms, players => [player(P) || P <- Ps]}}
    catch throw:Reason -> {error, Reason} end.

load_matches(Path, Competition, Kind) ->
    case soccer_csv:read(Path) of
        {ok, Rows} -> [match(R, Competition, Kind) || R <- Rows, valid_score(R, Kind)];
        {error, Reason} -> throw({cannot_load, Path, Reason})
    end.

valid_score(R, Kind) -> maps:get(home_key(Kind), R, <<>>) =/= <<>> andalso maps:get(away_key(Kind), R, <<>>) =/= <<>>.
home_key(brasileirao) -> <<"home_team">>; home_key(cup) -> <<"home_team">>; home_key(libertadores) -> <<"home_team">>; home_key(extended) -> <<"home">>; home_key(historical) -> <<"Equipe_mandante">>.
away_key(brasileirao) -> <<"away_team">>; away_key(cup) -> <<"away_team">>; away_key(libertadores) -> <<"away_team">>; away_key(extended) -> <<"away">>; away_key(historical) -> <<"Equipe_visitante">>.
goal_keys(brasileirao) -> {<<"home_goal">>, <<"away_goal">>}; goal_keys(cup) -> {<<"home_goal">>, <<"away_goal">>}; goal_keys(libertadores) -> {<<"home_goal">>, <<"away_goal">>}; goal_keys(extended) -> {<<"home_goal">>, <<"away_goal">>}; goal_keys(historical) -> {<<"Gols_mandante">>, <<"Gols_visitante">>}.
date_key(brasileirao) -> <<"datetime">>; date_key(cup) -> <<"datetime">>; date_key(libertadores) -> <<"datetime">>; date_key(extended) -> <<"date">>; date_key(historical) -> <<"Data">>.
season_key(historical) -> <<"Ano">>; season_key(_) -> <<"season">>.

match(R, Competition, Kind) ->
    {HG, AG} = goal_keys(Kind),
    Home = maps:get(home_key(Kind), R), Away = maps:get(away_key(Kind), R),
    Date = maps:get(date_key(Kind), R, <<>>),
    DateSort = parse_date(Date), Season0 = integer(maps:get(season_key(Kind), R, <<>>)),
    Season = case Season0 of 0 -> DateSort div 10000; _ -> Season0 end,
    #{date => Date, date_sort => DateSort, season => Season,
      competition => Competition, home => Home, away => Away, home_normalized => normalize_team(Home), away_normalized => normalize_team(Away),
      home_goals => number(maps:get(HG, R, <<>>)), away_goals => number(maps:get(AG, R, <<>>)),
      round => maps:get(round_key(Kind), R, <<>>), stage => maps:get(<<"stage">>, R, <<>>), source => Competition, raw => R}.
round_key(historical) -> <<"Rodada">>; round_key(extended) -> <<>>; round_key(_) -> <<"round">>.
player(R) -> #{id => maps:get(<<"ID">>, R, <<>>), name => maps:get(<<"Name">>, R, <<>>), age => integer(maps:get(<<"Age">>, R, <<>>)), nationality => maps:get(<<"Nationality">>, R, <<>>), overall => integer(maps:get(<<"Overall">>, R, <<>>)), potential => integer(maps:get(<<"Potential">>, R, <<>>)), club => maps:get(<<"Club">>, R, <<>>), position => maps:get(<<"Position">>, R, <<>>), jersey_number => maps:get(<<"Jersey Number">>, R, <<>>)}.
matches(Data) -> maps:get(matches, Data). players(Data) -> maps:get(players, Data).
number(B) -> case string:to_float(binary_to_list(B)) of {F, _} when is_float(F) -> trunc(F); {error, no_float} -> integer(B) end.
integer(B) -> try binary_to_integer(B) catch error:badarg -> 0 end.
parse_date(<<Y:4/binary,$-,M:2/binary,$-,D:2/binary,_/binary>>) -> binary_to_integer(<<Y/binary,M/binary,D/binary>>);
parse_date(<<D:2/binary,$/,M:2/binary,$/,Y:4/binary,_/binary>>) -> binary_to_integer(<<Y/binary,M/binary,D/binary>>);
parse_date(_) -> 0.
normalize_team(Value) ->
    Lower = lower_ascii(Value),
    NoAccent = lists:foldl(fun({From,To}, B) -> binary:replace(B, From, To, [global]) end, Lower,
                            [{<<195,161>>,<<"a">>},{<<195,160>>,<<"a">>},{<<195,162>>,<<"a">>},{<<195,163>>,<<"a">>},{<<195,169>>,<<"e">>},{<<195,170>>,<<"e">>},{<<195,173>>,<<"i">>},{<<195,179>>,<<"o">>},{<<195,180>>,<<"o">>},{<<195,181>>,<<"o">>},{<<195,186>>,<<"u">>},{<<195,167>>,<<"c">>}]),
    list_to_binary(string:trim(binary_to_list(re:replace(NoAccent, <<"[[:space:]]*[-(][a-z]{2,3}[)]?$">>, <<>>, [{return,binary}])))).
lower_ascii(B) -> << <<(if C >= $A, C =< $Z -> C + 32; true -> C end)>> || <<C>> <= B >>.
