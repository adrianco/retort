%%%-------------------------------------------------------------------
%%% @doc Feature: Statistical Analysis
%%%
%%% Goals per match, home advantage, biggest wins, season comparison
%%% and the knowledge graph traversals.
%%% @end
%%%-------------------------------------------------------------------
-module(statistics_SUITE).

-compile([export_all, nowarn_export_all]).

-include_lib("common_test/include/ct.hrl").
-include_lib("stdlib/include/assert.hrl").

all() ->
    [average_goals_per_match,
     home_advantage_rates_add_up,
     biggest_wins_are_ordered,
     compare_two_seasons,
     best_away_record,
     top_scoring_team_of_a_season,
     derbies_of_a_season,
     graph_neighbours_of_a_team,
     graph_path_between_two_clubs,
     dataset_summary_counts].

init_per_suite(Config) ->
    bdd:feature("Statistical Analysis"),
    bdd:data_is_loaded(),
    Config.

end_per_suite(_Config) -> ok.

%%--------------------------------------------------------------------
average_goals_per_match(_Config) ->
    bdd:scenario("What is the average number of goals per match?"),
    bdd:given("the match data is loaded", fun bdd:data_is_loaded/0),
    Stats = bdd:'when'("I ask for the Brasileirao statistics",
                       fun() ->
                               {ok, S} = br_query:competition_stats(
                                           #{competition => <<"brasileirao">>}),
                               S
                       end),
    bdd:then("the average should be a plausible football number",
             fun() ->
                     Avg = maps:get(goals_per_match, Stats),
                     ct:log("average goals per match: ~p", [Avg]),
                     ?assert(Avg > 2.0 andalso Avg < 3.5)
             end),
    bdd:'and'("it should equal total goals divided by matches",
              fun() ->
                      #{goals := G, matches := M, goals_per_match := Avg} = Stats,
                      ?assert(abs(Avg - G / M) < 0.01)
              end),
    bdd:'and'("home and away goals should sum to the total",
              fun() ->
                      #{goals := G, home_goals := HG, away_goals := AG} = Stats,
                      ?assertEqual(G, HG + AG)
              end).

%%--------------------------------------------------------------------
home_advantage_rates_add_up(_Config) ->
    bdd:scenario("Home wins, draws and away wins account for every match"),
    bdd:given("the match data is loaded", fun bdd:data_is_loaded/0),
    Stats = bdd:'when'("I ask for the 2019 Brasileirao statistics",
                       fun() ->
                               {ok, S} = br_query:competition_stats(
                                           #{competition => <<"serie a">>, season => 2019}),
                               S
                       end),
    bdd:then("the three outcomes should sum to the number of matches",
             fun() ->
                     #{matches := M, home_wins := H, away_wins := A, draws := D} = Stats,
                     ?assertEqual(380, M),
                     ?assertEqual(M, H + A + D)
             end),
    bdd:'and'("the rates should sum to 100 percent",
              fun() ->
                      #{home_win_rate := H, away_win_rate := A, draw_rate := D} = Stats,
                      ?assert(abs(H + A + D - 100.0) < 0.1)
              end),
    bdd:'and'("playing at home should be an advantage",
              fun() ->
                      ?assert(maps:get(home_win_rate, Stats) >
                                  maps:get(away_win_rate, Stats))
              end).

%%--------------------------------------------------------------------
biggest_wins_are_ordered(_Config) ->
    bdd:scenario("Show me the biggest wins in the data set"),
    bdd:given("the match data is loaded", fun bdd:data_is_loaded/0),
    Result = bdd:'when'("I ask for the biggest wins",
                        fun() ->
                                {ok, R} = br_query:biggest_wins(#{limit => 10}),
                                R
                        end),
    bdd:then("they should be sorted by margin, largest first",
             fun() ->
                     Margins = [maps:get(margin, M) || M <- maps:get(matches, Result)],
                     ct:log("margins: ~p", [Margins]),
                     ?assertEqual(lists:reverse(lists:sort(Margins)), Margins),
                     ?assert(hd(Margins) >= 6)
             end),
    bdd:'and'("the margin should match the score",
              fun() ->
                      lists:foreach(
                        fun(#{home_goals := H, away_goals := A, margin := M}) ->
                                ?assertEqual(abs(H - A), M)
                        end, maps:get(matches, Result))
              end),
    bdd:'and'("it can be narrowed to one competition and team",
              fun() ->
                      {ok, #{matches := Ms}} =
                          br_query:biggest_wins(#{competition => <<"serie a">>,
                                                  team => <<"Santos">>, limit => 3}),
                      lists:foreach(
                        fun(#{competition := C, home := H, away := A}) ->
                                ?assertEqual(<<"brasileirao_serie_a">>, C),
                                ?assert(H =:= <<"santos">> orelse A =:= <<"santos">>)
                        end, Ms)
              end).

%%--------------------------------------------------------------------
compare_two_seasons(_Config) ->
    bdd:scenario("Compare the 2018 and 2019 seasons"),
    bdd:given("the match data is loaded", fun bdd:data_is_loaded/0),
    Comparison = bdd:'when'("I compare 2018 with 2019",
                            fun() ->
                                    {ok, C} = br_query:compare_seasons(
                                                #{competition => <<"serie a">>,
                                                  season_a => 2018, season_b => 2019}),
                                    C
                            end),
    bdd:then("both seasons should have 380 matches",
             fun() ->
                     ?assertEqual(380, maps:get(matches, maps:get(season_a, Comparison))),
                     ?assertEqual(380, maps:get(matches, maps:get(season_b, Comparison)))
             end),
    bdd:'and'("the deltas should be the difference between the two",
              fun() ->
                      A = maps:get(goals, maps:get(season_a, Comparison)),
                      B = maps:get(goals, maps:get(season_b, Comparison)),
                      ?assertEqual(B - A, maps:get(goals, maps:get(deltas, Comparison)))
              end).

%%--------------------------------------------------------------------
best_away_record(_Config) ->
    bdd:scenario("Which team has the best away record?"),
    bdd:given("the match data is loaded", fun bdd:data_is_loaded/0),
    Rankings = bdd:'when'("I rank teams by away points in the 2018 Brasileirao",
                          fun() ->
                                  {ok, R} = br_query:team_rankings(
                                              #{competition => <<"serie a">>,
                                                season => 2018,
                                                venue => <<"away">>,
                                                limit => 5}),
                                  R
                          end),
    bdd:then("every team should have 19 away matches",
             fun() ->
                     lists:foreach(fun(R) -> ?assertEqual(19, maps:get(played, R)) end,
                                   maps:get(rankings, Rankings))
             end),
    bdd:'and'("the ranking should be ordered and consistent with the season table",
              fun() ->
                      [Best | _] = maps:get(rankings, Rankings),
                      {ok, Stats} = br_query:team_stats(
                                      #{team => maps:get(team, Best),
                                        competition => <<"serie a">>, season => 2018,
                                        venue => <<"away">>}),
                      ?assertEqual(maps:get(points, Best), maps:get(points, Stats)),
                      ?assertEqual(maps:get(wins, Best), maps:get(wins, Stats))
              end).

%%--------------------------------------------------------------------
top_scoring_team_of_a_season(_Config) ->
    bdd:scenario("Which team scored the most goals?"),
    bdd:given("the match data is loaded", fun bdd:data_is_loaded/0),
    {Rankings, Stats} =
        bdd:'when'("I rank the 2019 Brasileirao teams by goals scored",
                   fun() ->
                           {ok, R} = br_query:team_rankings(#{competition => <<"serie a">>,
                                                              season => 2019,
                                                              metric => <<"goals_for">>,
                                                              limit => 5}),
                           {ok, S} = br_query:competition_stats(
                                       #{competition => <<"serie a">>, season => 2019}),
                           {R, S}
                   end),
    bdd:then("the top scorer of the ranking and of the statistics should agree",
             fun() ->
                     [#{team_name := A} | _] = maps:get(rankings, Rankings),
                     [#{team_name := B} | _] = maps:get(top_scoring_teams, Stats),
                     ?assertEqual(A, B),
                     ?assertEqual(<<"Flamengo">>, A)
             end).

%%--------------------------------------------------------------------
derbies_of_a_season(_Config) ->
    bdd:scenario("Show me all derbies in 2023"),
    bdd:given("the match data is loaded", fun bdd:data_is_loaded/0),
    Derbies = bdd:'when'("I ask for the derbies of 2023",
                         fun() ->
                                 {ok, D} = br_query:derbies(#{season => 2023}),
                                 D
                         end),
    bdd:then("several derbies should be found",
             fun() ->
                     ?assert(length(maps:get(derbies, Derbies)) >= 10),
                     Names = [maps:get(derby, D) || D <- maps:get(derbies, Derbies)],
                     ?assert(lists:member(<<"Fla-Flu">>, Names)),
                     ?assert(lists:member(<<"Gre-Nal">>, Names))
             end),
    bdd:'and'("every fixture should be from 2023 and between the two rivals",
              fun() ->
                      lists:foreach(
                        fun(#{team_a := #{team := A}, team_b := #{team := B},
                              fixtures := Fixtures}) ->
                                lists:foreach(
                                  fun(#{season := S, home := H, away := Aw}) ->
                                          ?assertEqual(2023, S),
                                          ?assertEqual(lists:sort([A, B]),
                                                       lists:sort([H, Aw]))
                                  end, Fixtures)
                        end, maps:get(derbies, Derbies))
              end).

%%--------------------------------------------------------------------
graph_neighbours_of_a_team(_Config) ->
    bdd:scenario("Explore the knowledge graph around a club"),
    bdd:given("the graph is built", fun bdd:data_is_loaded/0),
    Result = bdd:'when'("I ask for the competitions Santos is connected to",
                        fun() ->
                                {ok, R} = br_query:graph_neighbors(
                                            #{node => <<"team:santos">>,
                                              relation => <<"played_in">>}),
                                R
                        end),
    bdd:then("the competition nodes should come back",
             fun() ->
                     Types = [maps:get(type, maps:get(node, N))
                              || N <- maps:get(neighbours, Result)],
                     ?assert(length(Types) >= 3),
                     lists:foreach(fun(T) -> ?assertEqual(competition, T) end, Types)
             end),
    bdd:'and'("a node can also be addressed by type and name",
              fun() ->
                      {ok, ByName} = br_query:graph_neighbors(#{type => <<"team">>,
                                                                name => <<"Santos FC">>,
                                                                relation => <<"played_in">>}),
                      ?assertEqual(maps:get(id, maps:get(node, Result)),
                                   maps:get(id, maps:get(node, ByName)))
              end).

%%--------------------------------------------------------------------
graph_path_between_two_clubs(_Config) ->
    bdd:scenario("Find how two clubs are connected"),
    bdd:given("the graph is built", fun bdd:data_is_loaded/0),
    Path = bdd:'when'("I ask for the path from Santos to Boca Juniors",
                      fun() ->
                              {ok, P} = br_query:graph_path(#{from => <<"team:santos">>,
                                                              to => <<"team:boca-juniors">>,
                                                              max_depth => 4}),
                              P
                      end),
    bdd:then("a path should exist",
             fun() ->
                     ?assertEqual(true, maps:get(found, Path)),
                     ct:log("~ts", [br_format:render(graph_path, Path)])
             end),
    bdd:'and'("it should start and end at the requested nodes",
              fun() ->
                      Nodes = [maps:get(id, maps:get(node, S)) || S <- maps:get(path, Path)],
                      ?assertEqual(<<"team:santos">>, hd(Nodes)),
                      ?assertEqual(<<"team:boca-juniors">>, lists:last(Nodes))
              end).

%%--------------------------------------------------------------------
dataset_summary_counts(_Config) ->
    bdd:scenario("The server reports what it has loaded"),
    bdd:given("the data is loaded", fun bdd:data_is_loaded/0),
    Summary = bdd:'when'("I ask for the data set summary",
                         fun() ->
                                 {ok, S} = br_query:dataset_summary(#{}),
                                 S
                         end),
    bdd:then("all six files should be listed",
             fun() -> ?assertEqual(6, length(maps:get(files, Summary))) end),
    bdd:'and'("the counts should be consistent",
              fun() ->
                      #{matches := M, teams := T, players := P,
                        graph_nodes := N, graph_edges := E} = Summary,
                      ?assert(M > 15000),
                      ?assert(T > 400),
                      ?assertEqual(18207, P),
                      ?assert(N > M),
                      ?assert(E > N)
              end).
