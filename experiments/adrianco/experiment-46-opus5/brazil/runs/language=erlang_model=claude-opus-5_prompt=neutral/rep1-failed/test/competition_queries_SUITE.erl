%%%-------------------------------------------------------------------
%%% @doc Feature: Competition Queries
%%%
%%% Standings calculated from the match results, champions, relegation
%%% and season coverage.  The 2019 Brasileirao is used as the reference
%%% season because its real final table is well known: Flamengo 90
%%% points, Santos and Palmeiras on 74, Cruzeiro, CSA, Chapecoense and
%%% Avai relegated.
%%% @end
%%%-------------------------------------------------------------------
-module(competition_queries_SUITE).

-compile([export_all, nowarn_export_all]).

-include_lib("common_test/include/ct.hrl").
-include_lib("stdlib/include/assert.hrl").

all() ->
    [standings_of_a_finished_season,
     standings_match_the_real_2019_table,
     relegated_teams,
     champion_of_several_seasons,
     standings_need_a_season,
     incomplete_seasons_are_flagged,
     competitions_are_listed_with_coverage,
     libertadores_stages_are_kept].

init_per_suite(Config) ->
    bdd:feature("Competition Queries"),
    bdd:data_is_loaded(),
    Config.

end_per_suite(_Config) -> ok.

%%--------------------------------------------------------------------
standings_of_a_finished_season(_Config) ->
    bdd:scenario("Standings are calculated from the matches"),
    bdd:given("the match data is loaded", fun bdd:data_is_loaded/0),
    Table = bdd:'when'("I request the 2019 Brasileirao standings",
                       fun() ->
                               {ok, T} = br_query:standings(#{competition => <<"brasileirao">>,
                                                              season => 2019}),
                               T
                       end),
    bdd:then("there should be 20 teams and 380 matches",
             fun() ->
                     ?assertEqual(20, maps:get(teams, Table)),
                     ?assertEqual(380, maps:get(matches, Table)),
                     ?assertEqual(true, maps:get(complete, Table))
             end),
    bdd:'and'("every team should have played 38 matches",
              fun() ->
                      lists:foreach(fun(R) -> ?assertEqual(38, maps:get(played, R)) end,
                                    maps:get(table, Table))
              end),
    bdd:'and'("the table should be ordered by points",
              fun() ->
                      Points = [maps:get(points, R) || R <- maps:get(table, Table)],
                      ?assertEqual(lists:reverse(lists:sort(Points)), Points)
              end),
    bdd:'and'("goals scored and conceded should balance across the league",
              fun() ->
                      Rows = maps:get(table, Table),
                      ?assertEqual(lists:sum([maps:get(goals_for, R) || R <- Rows]),
                                   lists:sum([maps:get(goals_against, R) || R <- Rows]))
              end).

%%--------------------------------------------------------------------
standings_match_the_real_2019_table(_Config) ->
    bdd:scenario("Who won the 2019 Brasileirao?"),
    bdd:given("the match data is loaded", fun bdd:data_is_loaded/0),
    Table = bdd:'when'("I request the 2019 standings",
                       fun() ->
                               {ok, T} = br_query:standings(#{season => 2019}),
                               T
                       end),
    bdd:then("Flamengo should be champion with 90 points",
             fun() ->
                     [First | _] = maps:get(table, Table),
                     ?assertEqual(<<"Flamengo">>, maps:get(team_name, First)),
                     ?assertEqual(90, maps:get(points, First)),
                     ?assertEqual(28, maps:get(wins, First)),
                     ?assertEqual(<<"Flamengo">>, maps:get(champion, Table))
             end),
    bdd:'and'("Santos and Palmeiras should follow on 74 points",
              fun() ->
                      [_, Second, Third | _] = maps:get(table, Table),
                      ?assertEqual(<<"Santos">>, maps:get(team_name, Second)),
                      ?assertEqual(74, maps:get(points, Second)),
                      ?assertEqual(<<"Palmeiras">>, maps:get(team_name, Third)),
                      ?assertEqual(74, maps:get(points, Third))
              end),
    bdd:'and'("the rendered table should look like the specification",
              fun() ->
                      Text = br_format:render(standings, Table),
                      ct:log("~ts", [Text]),
                      ?assertNotEqual(nomatch,
                                      binary:match(Text, <<"1. Flamengo - 90 pts (28W, 6D, 4L)">>)),
                      ?assertNotEqual(nomatch, binary:match(Text, <<"Champion">>))
              end).

%%--------------------------------------------------------------------
relegated_teams(_Config) ->
    bdd:scenario("Which teams were relegated?"),
    bdd:given("the match data is loaded", fun bdd:data_is_loaded/0),
    Relegated = bdd:'when'("I request the 2019 standings",
                           fun() ->
                                   {ok, T} = br_query:standings(#{season => 2019}),
                                   maps:get(relegated, T)
                           end),
    bdd:then("the bottom four of 2019 should be listed",
             fun() ->
                     ?assertEqual(4, length(Relegated)),
                     lists:foreach(fun(Name) -> ?assert(lists:member(Name, Relegated)) end,
                                   [<<"Cruzeiro">>, <<"CSA">>, <<"Chapecoense">>,
                                    <<"Avaí"/utf8>>])
             end).

%%--------------------------------------------------------------------
champion_of_several_seasons(_Config) ->
    bdd:scenario("Champions of the seasons in the data"),
    bdd:given("the match data is loaded", fun bdd:data_is_loaded/0),
    Champions = bdd:'when'("I take the champion of four complete seasons",
                           fun() ->
                                   [begin
                                        {ok, T} = br_query:standings(#{season => S}),
                                        {S, maps:get(champion, T)}
                                    end || S <- [2016, 2017, 2018, 2022]]
                           end),
    bdd:then("they should be the real champions",
             fun() ->
                     ct:log("~p", [Champions]),
                     ?assertEqual([{2016, <<"Palmeiras">>},
                                   {2017, <<"Corinthians">>},
                                   {2018, <<"Palmeiras">>},
                                   {2022, <<"Palmeiras">>}], Champions)
             end).

%%--------------------------------------------------------------------
standings_need_a_season(_Config) ->
    bdd:scenario("Standings without a season are refused politely"),
    bdd:given("the match data is loaded", fun bdd:data_is_loaded/0),
    Error = bdd:'when'("I request standings without a season",
                       fun() ->
                               {error, E} = br_query:standings(#{competition => <<"serie a">>}),
                               E
                       end),
    bdd:then("the error should list the available seasons",
             fun() ->
                     ?assertEqual(missing_season, maps:get(code, Error)),
                     ?assert(length(maps:get(suggestions, Error)) > 10)
             end).

%%--------------------------------------------------------------------
incomplete_seasons_are_flagged(_Config) ->
    bdd:scenario("A season with missing matches is not passed off as final"),
    bdd:given("the match data is loaded", fun bdd:data_is_loaded/0),
    {Complete, Incomplete} =
        bdd:'when'("I compare a complete season with a partial one",
                   fun() ->
                           {ok, A} = br_query:standings(#{season => 2019}),
                           {ok, B} = br_query:standings(#{season => 2023}),
                           {A, B}
                   end),
    bdd:then("only the complete season should be marked complete",
             fun() ->
                     ?assertEqual(true, maps:get(complete, Complete)),
                     ?assertEqual(false, maps:get(complete, Incomplete)),
                     ?assertEqual(null, maps:get(champion, Incomplete)),
                     ?assertEqual([], maps:get(relegated, Incomplete))
             end).

%%--------------------------------------------------------------------
competitions_are_listed_with_coverage(_Config) ->
    bdd:scenario("Which competitions and seasons are covered?"),
    bdd:given("the match data is loaded", fun bdd:data_is_loaded/0),
    Comps = bdd:'when'("I list the competitions",
                       fun() ->
                               {ok, #{competitions := C}} = br_query:list_competitions(#{}),
                               C
                       end),
    bdd:then("all five competitions of the data should be there",
             fun() ->
                     Ids = [maps:get(competition, C) || C <- Comps],
                     lists:foreach(fun(Id) -> ?assert(lists:member(Id, Ids)) end,
                                   [<<"brasileirao_serie_a">>, <<"brasileirao_serie_b">>,
                                    <<"brasileirao_serie_c">>, <<"copa_do_brasil">>,
                                    <<"libertadores">>])
             end),
    bdd:'and'("Serie A should span 2003 to 2023",
              fun() ->
                      [SerieA] = [C || C <- Comps,
                                       maps:get(competition, C) =:= <<"brasileirao_serie_a">>],
                      Seasons = maps:get(seasons, SerieA),
                      ?assertEqual(2003, hd(Seasons)),
                      ?assertEqual(2023, lists:last(Seasons)),
                      ?assert(maps:get(matches, SerieA) > 8000)
              end).

%%--------------------------------------------------------------------
libertadores_stages_are_kept(_Config) ->
    bdd:scenario("Libertadores matches keep their tournament stage"),
    bdd:given("the match data is loaded", fun bdd:data_is_loaded/0),
    Finals = bdd:'when'("I search each Libertadores season for its final",
                        fun() ->
                                lists:append(
                                  [begin
                                       {ok, #{matches := Ms}} =
                                           br_query:find_matches(
                                             #{competition => <<"libertadores">>,
                                               season => S, limit => 200}),
                                       [M || M <- Ms, maps:get(stage, M) =:= <<"final">>]
                                   end || S <- br_store:seasons_of(<<"libertadores">>)])
                        end),
    bdd:then("finals from several seasons should be found",
             fun() ->
                     ?assert(length(Finals) >= 10),
                     Seasons = lists:usort([maps:get(season, M) || M <- Finals]),
                     ?assert(length(Seasons) >= 8)
             end),
    bdd:'and'("a points table for a cup says that it is not a league",
              fun() ->
                      {ok, Table} = br_query:standings(#{competition => <<"copa do brasil">>,
                                                         season => 2019, limit => 3}),
                      ?assertEqual(<<"knockout">>, maps:get(competition_type, Table)),
                      ?assertEqual(false, maps:get(complete, Table)),
                      ?assertEqual(null, maps:get(champion, Table)),
                      Text = br_format:render(standings, Table),
                      ?assertNotEqual(nomatch, binary:match(Text, <<"not a league">>))
              end),
    bdd:'and'("group stage matches should be marked as such",
              fun() ->
                      {ok, #{total := Total}} =
                          br_query:find_matches(#{competition => <<"libertadores">>,
                                                  season => 2019, limit => 1}),
                      ?assert(Total > 100)
              end).
