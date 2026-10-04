%% BDD-style scenarios (Given / When / Then) run against the real Kaggle
%% datasets through the same tool interface an MCP client uses.
-module(bs_scenarios_tests).
-include_lib("eunit/include/eunit.hrl").

%% Given the match and player data is loaded
scenarios_test_() ->
    {setup, fun() -> ok = bs_data:ensure_loaded() end,
     {inparallel,
      [{atom_to_list(F), fun ?MODULE:F/0} || {F, 0} <- ?MODULE:module_info(exports),
                                             lists:prefix("s_", atom_to_list(F))]}}.

-compile([export_all, nowarn_export_all]).

%% --- helpers ---------------------------------------------------------------

%% When I call a tool ... the call succeeds within the time budget
ask(Tool, Args) -> ask(Tool, Args, 2000).

ask(Tool, Args, BudgetMs) ->
    {Us, Res} = timer:tc(fun() -> bs_tools:call(Tool, Args) end),
    ?assertMatch({Tool, {ok, _}}, {Tool, Res}),
    ?assert(Us div 1000 < BudgetMs),
    {ok, Text} = Res,
    ?assert(is_list(unicode:characters_to_list(Text))),   % valid UTF-8
    Text.

has(Text, Part) ->
    ?assertMatch({_, {_, _}}, {Part, binary:match(Text, Part)}).

lacks(Text, Part) -> ?assertEqual(nomatch, binary:match(Text, Part)).

key(Name) -> {ok, K} = bs_team:resolve(Name), K.

%% --- data coverage ---------------------------------------------------------

%% Then all six CSV files are loaded with the documented row counts
s_all_six_files_are_loaded() ->
    ?assertEqual([{brasileirao, 4180}, {novo_brasileirao, 6886}, {copa_do_brasil, 1337},
                  {libertadores, 1255}, {br_football, 10296}, {fifa_players, 18207}],
                 bs_data:sources()),
    [?assert(length(bs_query:matches(#{source => S, include_duplicates => true})) > 1000)
     || S <- [brasileirao, novo_brasileirao, copa_do_brasil, libertadores, br_football]],
    T = ask(<<"data_summary">>, #{}),
    has(T, <<"fifa_data.csv: 18207 rows">>),
    has(T, <<"Copa Libertadores">>).

%% Then overlapping files do not double count a match
s_overlapping_sources_are_deduplicated() ->
    [?assertEqual({S, 380}, {S, length(bs_query:matches(#{competition => serie_a, season => S}))})
     || S <- lists:seq(2006, 2022)],
    All = length(bs_query:matches(#{competition => serie_a, season => 2015, include_duplicates => true})),
    ?assert(All > 380).

%% --- 1. match queries ------------------------------------------------------

%% "Show me all Flamengo vs Fluminense matches"
s_matches_between_two_teams() ->
    T = ask(<<"search_matches">>, #{<<"team">> => <<"Flamengo">>, <<"opponent">> => <<"Fluminense">>}),
    has(T, <<"Flamengo vs Fluminense (Fla-Flu)">>),
    has(T, <<"Head-to-head in dataset">>),
    has(T, <<"more in dataset">>),
    %% each match has date, scores and competition
    Ms = bs_query:matches(#{team => key(<<"Flamengo">>), opponent => key(<<"Fluminense">>)}),
    ?assert(length(Ms) > 30),
    [begin
         ?assertMatch({_, _, _}, D),
         ?assert(is_integer(Hg) andalso is_integer(Ag)),
         ?assert(lists:member(C, [serie_a, copa_do_brasil, libertadores]))
     end || #{date := D, hg := Hg, ag := Ag, comp := C} <- Ms],
    ?assertMatch({match, _}, re:run(T, <<"- \\d{4}-\\d\\d-\\d\\d: \\S+ \\d+-\\d+ \\S+ \\(.+\\)">>, [unicode])).

%% "What matches did Palmeiras play in 2023?"
s_team_matches_in_a_season() ->
    T = ask(<<"search_matches">>, #{<<"team">> => <<"Palmeiras">>, <<"season">> => 2023}),
    has(T, <<"Palmeiras matches (2023)">>),
    has(T, <<"2023-">>),
    lacks(T, <<"2022-">>).

%% "Find all Copa do Brasil finals"
s_copa_do_brasil_finals() ->
    T = ask(<<"search_matches">>, #{<<"competition">> => <<"Copa do Brasil">>, <<"stage">> => <<"final">>}),
    has(T, <<"2013-11-27: Flamengo 2-0 Athletico-PR (Copa do Brasil 2013, final)">>),
    has(T, <<"2018-10-17: Corinthians 1-2 Cruzeiro">>).

%% "Show the 2018 Copa Libertadores bracket"
s_libertadores_knockout_stage() ->
    T = ask(<<"search_matches">>, #{<<"competition">> => <<"Libertadores">>, <<"season">> => 2018,
                                    <<"stage">> => <<"final">>}),
    has(T, <<"2018-12-09: River Plate 3-1 Boca Juniors">>),
    Semi = ask(<<"search_matches">>, #{<<"competition">> => <<"Libertadores">>, <<"season">> => 2018,
                                       <<"stage">> => <<"semifinals">>}),
    has(Semi, <<": 4 found">>).

%% Matches in a date range, both date formats accepted
s_matches_by_date_range() ->
    T = ask(<<"search_matches">>, #{<<"team">> => <<"Santos">>, <<"date_from">> => <<"2019-10-01">>,
                                    <<"date_to">> => <<"31/10/2019">>}),
    has(T, <<"2019-10-">>),
    lacks(T, <<"2019-11-">>),
    lacks(T, <<"2019-09-">>).

%% "When did Flamengo last play Corinthians?" / "What was the score?"
s_last_meeting_and_score() ->
    T = ask(<<"search_matches">>, #{<<"team">> => <<"Flamengo">>, <<"opponent">> => <<"Corinthians">>,
                                    <<"limit">> => 1}),
    [#{date := {Y, _, _}, hg := Hg, ag := Ag} | _] =
        bs_query:matches(#{team => key(<<"Flamengo">>), opponent => key(<<"Corinthians">>)}),
    ?assert(Y >= 2022),
    has(T, iolist_to_binary(io_lib:format("~p-~p", [Hg, Ag]))).

%% Home-only filter
s_home_matches_only() ->
    K = key(<<"Bahia">>),
    Ms = bs_query:matches(#{team => K, venue => home, season => 2019}),
    ?assert(Ms =/= []),
    ?assert(lists:all(fun(#{home := H}) -> H =:= K end, Ms)).

%% --- 2. team queries -------------------------------------------------------

%% "What is Corinthians' home record in 2022?"
s_home_record_in_season() ->
    T = ask(<<"team_stats">>, #{<<"team">> => <<"Corinthians">>, <<"season">> => 2022,
                                <<"venue">> => <<"home">>, <<"competition">> => <<"Brasileirão"/utf8>>}),
    has(T, <<"Corinthians home record (2022, Brasileirão)"/utf8>>),
    has(T, <<"- Matches: 19">>),
    has(T, <<"Win rate: ">>).

%% "Statistics for Palmeiras in season 2023": wins, losses, draws and goals
s_team_statistics_for_season() ->
    T = ask(<<"team_stats">>, #{<<"team">> => <<"Palmeiras">>, <<"season">> => <<"2023">>}),
    [has(T, P) || P <- [<<"Wins: ">>, <<"Draws: ">>, <<"Losses: ">>, <<"Goals For: ">>,
                        <<"Goals Against: ">>, <<"By competition:">>]],
    #{matches := N, wins := W, draws := D, losses := L} =
        bs_query:record(key(<<"Palmeiras">>), bs_query:matches(#{team => key(<<"Palmeiras">>), season => 2023})),
    ?assertEqual(N, W + D + L).

%% "Which team scored the most goals in Serie A 2019?"
s_most_goals_in_season() ->
    T = ask(<<"team_rankings">>, #{<<"metric">> => <<"most_goals">>, <<"competition">> => <<"Serie A">>,
                                   <<"season">> => 2019, <<"limit">> => 3}),
    has(T, <<"1. Flamengo - 38 matches, 28W 6D 4L, goals 86-37">>).

%% "Compare Palmeiras and Santos head-to-head"
s_head_to_head() ->
    T = ask(<<"head_to_head">>, #{<<"team_a">> => <<"Palmeiras">>, <<"team_b">> => <<"Santos">>}),
    has(T, <<"Palmeiras vs Santos">>),
    #{matches := Ms, a := #{wins := WA, draws := D, gf := GF}, b := #{wins := WB, draws := D, ga := GF}} =
        bs_query:head_to_head(key(<<"Palmeiras">>), key(<<"Santos">>), #{}),
    ?assertEqual(length(bs_query:played(Ms)), WA + WB + D),
    has(T, iolist_to_binary(io_lib:format("Palmeiras ~p wins, Santos ~p wins, ~p draws", [WA, WB, D]))).

%% "What competitions has Palmeiras played in?"
s_team_competitions() ->
    T = ask(<<"team_competitions">>, #{<<"team">> => <<"Palmeiras">>}),
    [has(T, C) || C <- [<<"Brasileirão"/utf8>>, <<"Copa do Brasil">>, <<"Copa Libertadores">>]].

%% Team name variations give identical answers
s_name_variations_give_same_answer() ->
    Q = fun(N) -> ask(<<"team_stats">>, #{<<"team">> => N, <<"season">> => 2018}) end,
    ?assertEqual(Q(<<"São Paulo"/utf8>>), Q(<<"Sao Paulo-SP">>)),
    ?assertEqual(Q(<<"São Paulo"/utf8>>), Q(<<"sao paulo fc">>)),
    ?assertEqual(Q(<<"Grêmio"/utf8>>), Q(<<"Gremio - RS">>)),
    ?assertEqual(Q(<<"Atlético Mineiro"/utf8>>), Q(<<"Atletico-MG">>)),
    ?assertNotEqual(key(<<"Atletico-MG">>), key(<<"Atletico-GO">>)),
    ?assertNotEqual(key(<<"Flamengo">>), key(<<"Flamengo - PI">>)).

%% --- 3. player queries -----------------------------------------------------

%% "Find all Brazilian players in the dataset" / "Who are the top Brazilian players?"
s_brazilian_players() ->
    T = ask(<<"search_players">>, #{<<"nationality">> => <<"Brazil">>, <<"limit">> => 5}),
    has(T, <<"Players found: 827">>),
    has(T, <<"1. Neymar Jr - Overall: 92, Position: LW, Club: Paris Saint-Germain">>),
    Ovs = [O || #{overall := O} <- bs_query:players(#{nationality => <<"brasil">>})],
    ?assertEqual(lists:reverse(lists:sort(Ovs)), Ovs).

%% "Who is Neymar?" / name search is accent-insensitive
s_player_lookup_by_name() ->
    T = ask(<<"player_details">>, #{<<"name">> => <<"neymar">>}),
    [has(T, P) || P <- [<<"Neymar Jr">>, <<"Nationality: Brazil">>, <<"Overall: 92">>, <<"Dribbling 96">>]],
    %% every word of the query has to match, in any order
    ?assertMatch([#{name := <<"Cristiano Ronaldo">>} | _], bs_query:players(#{name => <<"ronaldo cristiano">>})),
    ?assertMatch({error, _}, bs_tools:call(<<"player_details">>, #{<<"name">> => <<"Zzzqqq">>})).

%% "Who are the highest-rated players at Grêmio?" (club filter)
s_players_by_club() ->
    T = ask(<<"search_players">>, #{<<"club">> => <<"Gremio">>}),
    has(T, <<"Players found: 20">>),
    has(T, <<"Club: Grêmio"/utf8>>),
    %% Santos must not pull in Santos Laguna (Mexico)
    ?assert(lists:all(fun(#{club := C}) -> C =:= <<"Santos">> end, bs_query:players(#{club => <<"Santos">>}))),
    %% clubs missing from the FIFA file are reported honestly
    has(ask(<<"search_players">>, #{<<"club">> => <<"Flamengo">>}), <<"Players found: 0">>).

%% "Show me all forwards from Santos"
s_forwards_at_club() ->
    Ps = bs_query:players(#{club => <<"Santos">>, position => <<"forwards">>}),
    ?assert(Ps =/= []),
    ?assert(lists:all(fun(#{position := P}) -> lists:member(P, bs_query:position_group(<<"forward">>)) end, Ps)),
    has(ask(<<"search_players">>, #{<<"club">> => <<"Santos">>, <<"position">> => <<"forward">>}), <<"Position: ST">>).

%% "Brazilian players at Brazilian clubs"
s_brazilian_players_by_club() ->
    T = ask(<<"club_player_summary">>, #{}),
    has(T, <<"Brazil players at Brazilian clubs">>),
    has(T, <<"- Cruzeiro: 20 players (avg rating: ">>),
    lacks(T, <<"Real Madrid">>),
    has(ask(<<"club_player_summary">>, #{<<"brazilian_clubs_only">> => false, <<"limit">> => 400}),
        <<"Real Madrid">>).

%% Rating filter
s_players_by_rating() ->
    Ps = bs_query:players(#{min_overall => 90}),
    ?assert(length(Ps) > 3),
    ?assert(lists:all(fun(#{overall := O}) -> O >= 90 end, Ps)).

%% --- 4. competition queries ------------------------------------------------

%% "Who won the 2019 Brasileirão?"
s_champion_2019() ->
    T = ask(<<"standings">>, #{<<"season">> => 2019}, 5000),
    has(T, <<"2019 Brasileirão Final Standings (calculated from matches):"/utf8>>),
    has(T, <<"1. Flamengo - 90 pts (28W, 6D, 4L)">>),
    has(T, <<"- Champion">>),
    has(T, <<"2. Santos - 74 pts (22W, 8D, 8L)">>),
    has(T, <<"3. Palmeiras - 74 pts (21W, 11D, 6L)">>).

%% "Which teams were relegated in 2020?"
s_relegated_2020() ->
    T = ask(<<"standings">>, #{<<"season">> => 2020, <<"competition">> => <<"Brasileirão"/utf8>>}, 5000),
    [has(T, <<Team/binary, " - Relegated">>) || Team <- [<<"GD -19">>, <<"GD -22">>, <<"GD -23">>, <<"GD -30">>]],
    Bottom = [bs_team:display(K) || {K, _} <- lists:nthtail(16, bs_query:standings(
                                                  bs_query:matches(#{competition => serie_a, season => 2020})))],
    ?assertEqual([<<"Vasco">>, <<"Goiás"/utf8>>, <<"Coritiba">>, <<"Botafogo">>], Bottom).

%% Older seasons come from the historical file
s_historical_season_standings() ->
    T = ask(<<"standings">>, #{<<"season">> => 2003}, 5000),
    has(T, <<"1. Cruzeiro - 100 pts">>).

s_unknown_season_is_an_error() ->
    ?assertMatch({error, <<"No ", _/binary>>}, bs_tools:call(<<"standings">>, #{<<"season">> => 1950})).

%% --- 5. statistical analysis -----------------------------------------------

%% "What's the average goals per match in the Brasileirão?"
s_average_goals() ->
    T = ask(<<"season_summary">>, #{<<"competition">> => <<"Brasileirão"/utf8>>}, 5000),
    has(T, <<"Average goals per match: 2.">>),
    has(T, <<"Home win rate: ">>),
    #{avg_goals := Avg, home_win_rate := HW} =
        bs_query:league_stats(bs_query:matches(#{competition => serie_a})),
    ?assert(Avg > 2.0 andalso Avg < 3.2),
    ?assert(HW > 40 andalso HW < 60).

%% "Which team has the best home / away record?"
s_best_home_and_away_record() ->
    H = ask(<<"team_rankings">>, #{<<"metric">> => <<"best_home_record">>, <<"competition">> => <<"Serie A">>,
                                   <<"min_matches">> => 100}, 5000),
    has(H, <<"Best home records">>),
    has(H, <<"1. ">>),
    A = ask(<<"team_rankings">>, #{<<"metric">> => <<"best_away_record">>, <<"season">> => 2019,
                                   <<"competition">> => <<"Serie A">>}, 5000),
    has(A, <<"1. Flamengo - 19 matches">>).

%% "Show me the biggest wins in the dataset"
s_biggest_wins() ->
    T = ask(<<"biggest_wins">>, #{<<"limit">> => 5}, 5000),
    has(T, <<"1. 2021-06-08: São Paulo 9-1"/utf8>>),
    [#{hg := H1, ag := A1}, #{hg := H2, ag := A2} | _] = bs_query:biggest_wins(bs_query:matches(#{}), 5),
    ?assert(abs(H1 - A1) >= abs(H2 - A2)).

%% "Compare the 2018 and 2019 seasons"
s_compare_seasons() ->
    T = ask(<<"compare_seasons">>, #{<<"season_a">> => 2018, <<"season_b">> => 2019}, 5000),
    has(T, <<"Top of table: Palmeiras (80 pts)">>),
    has(T, <<"Top of table: Flamengo (90 pts)">>).

%% "Show me all derbies in 2023"
s_derbies_in_season() ->
    T = ask(<<"derbies">>, #{<<"season">> => 2023, <<"limit">> => 100}),
    has(T, <<"[Fla-Flu]">>),
    has(T, <<"[Grenal]">>),
    lacks(T, <<"2022-">>).

%% --- cross-file ------------------------------------------------------------

%% Match history (several match files) + FIFA squad for one club
s_cross_file_team_profile() ->
    T = ask(<<"team_profile">>, #{<<"team">> => <<"Cruzeiro">>}),
    [has(T, P) || P <- [<<"Brasileirão (2003-"/utf8>>, <<"Copa Libertadores">>, <<"FIFA squad:">>,
                        <<"20 players, average rating">>, <<"Club: Cruzeiro">>]].

%% Extended statistics file contributes lower divisions
s_lower_divisions_from_extended_file() ->
    T = ask(<<"search_matches">>, #{<<"competition">> => <<"Serie B">>, <<"season">> => 2019, <<"limit">> => 3}),
    has(T, <<"Série B 2019"/utf8>>).

%% --- error handling --------------------------------------------------------

s_bad_arguments_are_reported() ->
    ?assertMatch({error, <<"No team matching", _/binary>>},
                 bs_tools:call(<<"team_stats">>, #{<<"team">> => <<"Qwertyuiop">>})),
    ?assertMatch({error, <<"Missing required argument", _/binary>>}, bs_tools:call(<<"team_stats">>, #{})),
    ?assertMatch({error, <<"Unknown competition", _/binary>>},
                 bs_tools:call(<<"search_matches">>, #{<<"competition">> => <<"NBA">>})),
    ?assertMatch({error, _}, bs_tools:call(<<"search_matches">>, #{<<"date_from">> => <<"yesterday">>})),
    ?assertMatch({error, _}, bs_tools:call(<<"standings">>, #{<<"season">> => <<"abc">>})),
    ?assertEqual({error, unknown_tool}, bs_tools:call(<<"nope">>, #{})).
