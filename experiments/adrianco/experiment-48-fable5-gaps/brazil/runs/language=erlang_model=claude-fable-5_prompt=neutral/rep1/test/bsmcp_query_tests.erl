%% BDD-style scenarios (Given the match/player data is loaded / When ... /
%% Then ...) exercising the query layer against the real CSV files.
-module(bsmcp_query_tests).
-include_lib("eunit/include/eunit.hrl").

query_test_() ->
    {setup,
     fun() -> {ok, _} = bsmcp_data:ensure_loaded() end,
     fun(_) -> ok end,
     {timeout, 120,
      [{"all six CSV files load and are queryable", fun files_loaded/0},
       {"find matches between Flamengo and Fluminense", fun fla_flu/0},
       {"team stats for Palmeiras in 2023", fun palmeiras_2023/0},
       {"Corinthians home record in 2022", fun corinthians_home_2022/0},
       {"2019 Brasileirão champion is Flamengo with 90 points", fun standings_2019/0},
       {"2003 Brasileirão champion is Cruzeiro with 100 points", fun standings_2003/0},
       {"head-to-head Palmeiras vs Santos is consistent", fun h2h_consistent/0},
       {"team name variations resolve to the same team", fun name_variants/0},
       {"date range filter", fun date_range/0},
       {"Copa do Brasil finals are labeled", fun cup_finals/0},
       {"Libertadores finals via stage filter", fun libertadores_finals/0},
       {"player search by name finds Neymar", fun find_neymar/0},
       {"Brazilian players filter and rating sort", fun brazilian_players/0},
       {"position role keyword expansion", fun position_roles/0},
       {"league-wide averages are sane", fun league_averages/0},
       {"biggest wins are ordered by margin", fun biggest_wins/0},
       {"unknown team gives a clear error", fun unknown_team/0},
       {"cross-source duplicates were removed", fun dedup/0}]}}.

%% Scenario: all datasets loaded
files_loaded() ->
    S = bsmcp_data:summary(),
    Files = maps:get(files, S),
    ?assertEqual(6, map_size(Files)),
    %% every file contributed rows
    [?assert(N > 0) || {_, N} <- maps:to_list(Files)],
    ?assert(maps:get(matches, S) > 15000),
    ?assertEqual(18207, maps:get(players, S)).

%% Scenario: Given the match data is loaded, When I search for matches
%% between "Flamengo" and "Fluminense", Then I should receive a list of
%% matches, And each match should have date, scores, and competition.
fla_flu() ->
    {ok, R} = bsmcp_query:search_matches(#{team1 => <<"Flamengo">>,
                                           team2 => <<"Fluminense">>}),
    Ms = maps:get(matches, R),
    ?assert(length(Ms) >= 20),
    lists:foreach(
      fun(M) ->
              ?assertMatch({_, _, _}, maps:get(date, M)),
              ?assert(is_integer(maps:get(hg, M))),
              ?assert(is_integer(maps:get(ag, M))),
              ?assert(is_binary(maps:get(competition, M)))
      end, Ms),
    #{t1_wins := W1, t2_wins := W2, draws := D} = maps:get(h2h, R),
    ?assertEqual(length(Ms), W1 + W2 + D).

%% Scenario: Given the match data is loaded, When I request statistics for
%% "Palmeiras" in season "2023", Then I should receive wins, losses, draws,
%% and goals.
palmeiras_2023() ->
    {ok, S} = bsmcp_query:team_stats(<<"Palmeiras">>, #{season => 2023}),
    #{overall := #{played := P, wins := W, draws := D, losses := L,
                   gf := GF, ga := GA}} = S,
    ?assert(P > 0),
    ?assertEqual(P, W + D + L),
    ?assert(GF > 0),
    ?assert(GA >= 0).

corinthians_home_2022() ->
    {ok, S} = bsmcp_query:team_stats(<<"Corinthians">>,
                                     #{season => 2022,
                                       competition => <<"brasileirao">>,
                                       venue => <<"home">>}),
    #{overall := O = #{played := P, wins := W}} = S,
    %% 19 home fixtures in a 38-round season; the dataset is missing scores
    %% for a few, so accept the with-result subset.
    ?assert(P >= 16 andalso P =< 19),
    ?assert(W >= 10),
    ?assertEqual(P, maps:get(wins, O) + maps:get(draws, O) + maps:get(losses, O)).

%% Matches the worked example in the specification.
standings_2019() ->
    {ok, St} = bsmcp_query:standings(<<"brasileirao">>, 2019),
    ?assertEqual(380, maps:get(matches, St)),
    [Top | _] = maps:get(rows, St),
    ?assertEqual(<<"Flamengo">>, maps:get(display, Top)),
    ?assertEqual(90, maps:get(pts, Top)),
    ?assertEqual(28, maps:get(wins, Top)),
    ?assertEqual(6, maps:get(draws, Top)),
    ?assertEqual(4, maps:get(losses, Top)),
    ?assertEqual(20, length(maps:get(rows, St))).

%% Historically correct record season (24 teams, 46 rounds).
standings_2003() ->
    {ok, St} = bsmcp_query:standings(<<"Serie A">>, 2003),
    [Top | _] = maps:get(rows, St),
    ?assertEqual(<<"Cruzeiro">>, maps:get(display, Top)),
    ?assertEqual(100, maps:get(pts, Top)),
    ?assertEqual(24, length(maps:get(rows, St))).

h2h_consistent() ->
    {ok, R} = bsmcp_query:head_to_head(<<"Palmeiras">>, <<"Santos">>),
    #{t1_wins := W1, t2_wins := W2, draws := D} = maps:get(h2h, R),
    ?assert(maps:get(total, R) > 0),
    Decided = [M || M <- maps:get(matches, R),
                    maps:get(hg, M) =/= undefined,
                    maps:get(ag, M) =/= undefined],
    ?assertEqual(length(Decided), W1 + W2 + D).

%% Scenario: "Palmeiras-SP", "Palmeiras" and "palmeiras" are the same team.
name_variants() ->
    {ok, A} = bsmcp_query:search_matches(#{team1 => <<"Palmeiras-SP">>}),
    {ok, B} = bsmcp_query:search_matches(#{team1 => <<"Palmeiras">>}),
    {ok, C} = bsmcp_query:search_matches(#{team1 => <<"palmeiras">>}),
    ?assert(maps:get(total, A) > 100),
    ?assertEqual(maps:get(total, A), maps:get(total, B)),
    ?assertEqual(maps:get(total, B), maps:get(total, C)),
    {ok, D} = bsmcp_query:search_matches(#{team1 => <<"São Paulo"/utf8>>}),
    {ok, E} = bsmcp_query:search_matches(#{team1 => <<"Sao Paulo">>}),
    ?assertEqual(maps:get(total, D), maps:get(total, E)).

date_range() ->
    {ok, R} = bsmcp_query:search_matches(#{team1 => <<"Flamengo">>,
                                           date_from => <<"2019-01-01">>,
                                           date_to => <<"2019-12-31">>}),
    ?assert(maps:get(total, R) > 30),
    lists:foreach(fun(M) -> ?assertMatch({2019, _, _}, maps:get(date, M)) end,
                  maps:get(matches, R)).

cup_finals() ->
    {ok, R} = bsmcp_query:search_matches(#{competition => <<"Copa do Brasil">>,
                                           stage => <<"final">>}),
    ?assert(maps:get(total, R) >= 20),
    lists:foreach(
      fun(M) ->
              ?assertEqual(<<"Copa do Brasil">>, maps:get(competition, M)),
              ?assertEqual(<<"final">>, maps:get(stage, M))
      end, maps:get(matches, R)).

libertadores_finals() ->
    {ok, R} = bsmcp_query:search_matches(#{competition => <<"libertadores">>,
                                           stage => <<"final">>}),
    ?assert(maps:get(total, R) >= 10),
    %% "final" must not match "semifinals"
    lists:foreach(
      fun(M) -> ?assertEqual(<<"final">>, maps:get(stage, M)) end,
      maps:get(matches, R)).

find_neymar() ->
    {ok, Ps} = bsmcp_query:search_players(#{name => <<"neymar">>}),
    ?assertMatch([_ | _], Ps),
    Top = hd(Ps),
    ?assertEqual(<<"Neymar Jr">>, maps:get(name, Top)),
    ?assertEqual(<<"Brazil">>, maps:get(nationality, Top)),
    ?assertEqual(92, maps:get(overall, Top)).

brazilian_players() ->
    {ok, Ps} = bsmcp_query:search_players(#{nationality => <<"Brazilian">>}),
    ?assert(length(Ps) > 500),
    lists:foreach(fun(P) -> ?assertEqual(<<"Brazil">>, maps:get(nationality, P)) end,
                  Ps),
    %% sorted by overall, best Brazilian first
    ?assertEqual(<<"Neymar Jr">>, maps:get(name, hd(Ps))),
    Ovs = [maps:get(overall, P) || P <- Ps],
    ?assertEqual(Ovs, lists:reverse(lists:sort(Ovs))).

position_roles() ->
    {ok, GKs} = bsmcp_query:search_players(#{nationality => <<"Brazil">>,
                                             position => <<"goalkeeper">>}),
    ?assert(length(GKs) > 10),
    lists:foreach(fun(P) -> ?assertEqual(<<"GK">>, maps:get(position, P)) end, GKs),
    {ok, Fwds} = bsmcp_query:search_players(#{position => <<"forward">>,
                                              min_overall => 90}),
    ?assert(length(Fwds) > 0),
    lists:foreach(fun(P) -> ?assert(maps:get(overall, P) >= 90) end, Fwds).

league_averages() ->
    {ok, S} = bsmcp_query:league_stats(#{competition => <<"brasileirao">>}),
    ?assert(maps:get(matches, S) > 5000),
    Avg = maps:get(avg_goals, S),
    ?assert(Avg > 1.5 andalso Avg < 4.0),
    ?assert(abs(maps:get(home_win_pct, S) + maps:get(draw_pct, S) +
                    maps:get(away_win_pct, S) - 100.0) < 0.001),
    %% home advantage is real in Brazil
    ?assert(maps:get(home_win_pct, S) > maps:get(away_win_pct, S)).

biggest_wins() ->
    {ok, Ms} = bsmcp_query:biggest_wins(#{}),
    Margins = [abs(maps:get(hg, M) - maps:get(ag, M)) || M <- lists:sublist(Ms, 50)],
    ?assertEqual(Margins, lists:reverse(lists:sort(Margins))),
    ?assert(hd(Margins) >= 6).

unknown_team() ->
    ?assertMatch({error, {unknown_team, _}},
                 bsmcp_query:search_matches(#{team1 => <<"Manchester United">>})),
    ?assertMatch({error, {unknown_team, _}},
                 bsmcp_query:team_stats(<<"zzz no such team">>, #{})).

%% The two Brasileirão sources overlap 2012-2019 and the extended stats file
%% overlaps everything; per-season match counts must stay at one source's worth.
dedup() ->
    ?assert(maps:get(duplicates_skipped, bsmcp_data:summary()) > 5000),
    Count2015 = length([M || M <- bsmcp_data:matches(),
                             maps:get(season, M) =:= 2015,
                             maps:get(competition, M) =:=
                                 <<"Brasileirão Série A"/utf8>>]),
    ?assertEqual(380, Count2015).
