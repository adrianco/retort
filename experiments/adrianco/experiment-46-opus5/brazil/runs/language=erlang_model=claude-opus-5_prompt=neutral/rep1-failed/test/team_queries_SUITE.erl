%%%-------------------------------------------------------------------
%%% @doc Feature: Team Queries
%%%
%%% Match history, win/loss/draw records, goals, per-competition
%%% performance and head-to-head comparison.
%%% @end
%%%-------------------------------------------------------------------
-module(team_queries_SUITE).

-compile([export_all, nowarn_export_all]).

-include_lib("common_test/include/ct.hrl").
-include_lib("stdlib/include/assert.hrl").

all() ->
    [team_statistics_for_a_season,
     home_record_matches_the_specification_layout,
     home_and_away_split_adds_up,
     head_to_head_between_two_teams,
     head_to_head_recognises_a_derby,
     team_profile_spans_all_competitions,
     team_rankings_find_the_best_home_record,
     list_teams_by_state].

init_per_suite(Config) ->
    bdd:feature("Team Queries"),
    bdd:data_is_loaded(),
    Config.

end_per_suite(_Config) -> ok.

%%--------------------------------------------------------------------
team_statistics_for_a_season(_Config) ->
    bdd:scenario("Get team statistics"),
    bdd:given("the match data is loaded", fun bdd:data_is_loaded/0),
    Stats = bdd:'when'("I request statistics for \"Palmeiras\" in season \"2022\"",
                       fun() ->
                               {ok, S} = br_query:team_stats(#{team => <<"Palmeiras">>,
                                                               season => 2022,
                                                               competition => <<"serie a">>}),
                               S
                       end),
    bdd:then("I should receive wins, losses, draws and goals",
             fun() ->
                     lists:foreach(fun(Key) ->
                                           ?assert(is_integer(maps:get(Key, Stats)))
                                   end,
                                   [played, wins, draws, losses, goals_for,
                                    goals_against, goal_difference, points])
             end),
    bdd:'and'("a 38 round league season should have 38 matches",
              fun() -> ?assertEqual(38, maps:get(played, Stats)) end),
    bdd:'and'("wins, draws and losses should add up to the matches played",
              fun() ->
                      #{played := P, wins := W, draws := D, losses := L} = Stats,
                      ?assertEqual(P, W + D + L)
              end),
    bdd:'and'("points should follow the three points for a win rule",
              fun() ->
                      #{wins := W, draws := D, points := Pts} = Stats,
                      ?assertEqual(W * 3 + D, Pts)
              end),
    bdd:but("an incomplete season is reported as it is, not padded",
            fun() ->
                    %% The 2023 Serie A is only present in BR-Football-Dataset.csv,
                    %% which is missing a handful of fixtures: the query returns
                    %% what the data contains.
                    {ok, S2023} = br_query:team_stats(#{team => <<"Palmeiras">>,
                                                        season => 2023,
                                                        competition => <<"serie a">>}),
                    ?assert(maps:get(played, S2023) =< 38),
                    {ok, Table} = br_query:standings(#{competition => <<"serie a">>,
                                                       season => 2023}),
                    ?assertEqual(false, maps:get(complete, Table))
            end).

%%--------------------------------------------------------------------
home_record_matches_the_specification_layout(_Config) ->
    bdd:scenario("Corinthians' home record in 2022"),
    bdd:given("the match data is loaded", fun bdd:data_is_loaded/0),
    {Stats, Text} =
        bdd:'when'("I ask for the Corinthians home record of the 2022 Brasileirao",
                   fun() ->
                           {ok, S} = br_query:team_stats(#{team => <<"Corinthians">>,
                                                           season => 2022,
                                                           competition => <<"serie a">>,
                                                           venue => <<"home">>}),
                           {S, br_format:render(team_stats, S)}
                   end),
    bdd:then("there should be 19 home matches",
             fun() -> ?assertEqual(19, maps:get(played, Stats)) end),
    bdd:'and'("the text should be laid out as in the specification",
              fun() ->
                      ct:log("~ts", [Text]),
                      lists:foreach(
                        fun(Needle) ->
                                ?assertNotEqual(nomatch, binary:match(Text, Needle))
                        end,
                        [<<"Corinthians home record">>, <<"- Matches: 19">>,
                         <<"- Wins: ">>, <<"Draws: ">>, <<"Losses: ">>,
                         <<"- Goals For: ">>, <<"Goals Against: ">>,
                         <<"- Win rate: ">>])
              end).

%%--------------------------------------------------------------------
home_and_away_split_adds_up(_Config) ->
    bdd:scenario("Home and away records add up to the overall record"),
    bdd:given("the match data is loaded", fun bdd:data_is_loaded/0),
    Stats = bdd:'when'("I request the 2019 record of Gremio",
                       fun() ->
                               {ok, S} = br_query:team_stats(#{team => <<"Gremio">>,
                                                               season => 2019}),
                               S
                       end),
    bdd:then("home plus away should equal the total",
             fun() ->
                     #{played := P, wins := W, goals_for := GF,
                       home := #{played := HP, wins := HW, goals_for := HGF},
                       away := #{played := AP, wins := AW, goals_for := AGF}} = Stats,
                     ?assertEqual(P, HP + AP),
                     ?assertEqual(W, HW + AW),
                     ?assertEqual(GF, HGF + AGF)
             end).

%%--------------------------------------------------------------------
head_to_head_between_two_teams(_Config) ->
    bdd:scenario("Compare Palmeiras and Santos head-to-head"),
    bdd:given("the match data is loaded", fun bdd:data_is_loaded/0),
    H2H = bdd:'when'("I compare Palmeiras and Santos",
                     fun() ->
                             {ok, R} = br_query:head_to_head(#{team_a => <<"Palmeiras">>,
                                                               team_b => <<"Santos">>,
                                                               limit => 5}),
                             R
                     end),
    bdd:then("wins, draws and losses should add up to the matches played",
             fun() ->
                     #{played := P, team_a_wins := AW, team_b_wins := BW,
                       draws := D} = H2H,
                     ?assert(P > 30),
                     ?assertEqual(P, AW + BW + D)
             end),
    bdd:'and'("only the requested number of matches should be listed",
              fun() -> ?assertEqual(5, length(maps:get(matches, H2H))) end),
    bdd:'and'("the totals should agree with the per team records",
              fun() ->
                      #{team_a_wins := AW, team_a_goals := AG} = H2H,
                      {ok, Ms} = br_query:find_matches(#{team => <<"Palmeiras">>,
                                                         opponent => <<"Santos">>,
                                                         limit => 500}),
                      Wins = length([1 || #{home := H, home_goals := HG,
                                            away_goals := AGoals} <- maps:get(matches, Ms),
                                          (H =:= <<"palmeiras">> andalso HG > AGoals)
                                              orelse (H =/= <<"palmeiras">>
                                                      andalso AGoals > HG)]),
                      ?assertEqual(Wins, AW),
                      ?assert(AG > 0)
              end).

%%--------------------------------------------------------------------
head_to_head_recognises_a_derby(_Config) ->
    bdd:scenario("The Fla-Flu is recognised as a derby"),
    bdd:given("the match data is loaded", fun bdd:data_is_loaded/0),
    H2H = bdd:'when'("I compare Flamengo and Fluminense",
                     fun() ->
                             {ok, R} = br_query:head_to_head(#{team_a => <<"Flamengo">>,
                                                               team_b => <<"Fluminense">>}),
                             R
                     end),
    bdd:then("the derby should be named",
             fun() -> ?assertEqual(<<"Fla-Flu">>, maps:get(derby, H2H)) end),
    bdd:'and'("a non rivalry should have no derby name",
              fun() ->
                      {ok, Other} = br_query:head_to_head(#{team_a => <<"Santos">>,
                                                            team_b => <<"Gremio">>}),
                      ?assertEqual(null, maps:get(derby, Other))
              end).

%%--------------------------------------------------------------------
team_profile_spans_all_competitions(_Config) ->
    bdd:scenario("What competitions has Palmeiras played in?"),
    bdd:given("the match data is loaded", fun bdd:data_is_loaded/0),
    Profile = bdd:'when'("I ask for the Palmeiras profile",
                         fun() ->
                                 {ok, P} = br_query:team_profile(#{team => <<"Palmeiras">>}),
                                 P
                         end),
    bdd:then("all three competitions should be listed",
             fun() ->
                     Comps = [maps:get(competition, C)
                              || C <- maps:get(by_competition, Profile)],
                     ?assert(lists:member(<<"brasileirao_serie_a">>, Comps)),
                     ?assert(lists:member(<<"copa_do_brasil">>, Comps)),
                     ?assert(lists:member(<<"libertadores">>, Comps))
             end),
    bdd:'and'("the per competition records should sum to the overall record",
              fun() ->
                      #{overall := #{played := Total}} = Profile,
                      Sum = lists:sum([maps:get(played, C)
                                       || C <- maps:get(by_competition, Profile)]),
                      ?assertEqual(Total, Sum)
              end),
    bdd:'and'("the club's derbies should be listed",
              fun() ->
                      Derbies = [maps:get(derby, R) || R <- maps:get(rivals, Profile)],
                      ?assert(lists:member(<<"Derby Paulista"/utf8>>, Derbies))
              end).

%%--------------------------------------------------------------------
team_rankings_find_the_best_home_record(_Config) ->
    bdd:scenario("Which team has the best home record?"),
    bdd:given("the match data is loaded", fun bdd:data_is_loaded/0),
    Rankings = bdd:'when'("I rank teams by points won at home in the 2019 Brasileirao",
                          fun() ->
                                  {ok, R} = br_query:team_rankings(
                                              #{competition => <<"serie a">>,
                                                season => 2019,
                                                venue => <<"home">>,
                                                metric => <<"points">>,
                                                limit => 5}),
                                  R
                          end),
    bdd:then("the list should be ordered by points",
             fun() ->
                     Points = [maps:get(points, R) || R <- maps:get(rankings, Rankings)],
                     ?assertEqual(lists:reverse(lists:sort(Points)), Points)
             end),
    bdd:'and'("every team should have played 19 home matches",
              fun() ->
                      lists:foreach(fun(R) -> ?assertEqual(19, maps:get(played, R)) end,
                                    maps:get(rankings, Rankings))
              end),
    bdd:'and'("the 2019 champion should top the home table",
              fun() ->
                      [#{team_name := Best} | _] = maps:get(rankings, Rankings),
                      ?assertEqual(<<"Flamengo">>, Best)
              end).

%%--------------------------------------------------------------------
list_teams_by_state(_Config) ->
    bdd:scenario("List the teams of one state"),
    bdd:given("the match data is loaded", fun bdd:data_is_loaded/0),
    Teams = bdd:'when'("I list the teams from Rio de Janeiro",
                       fun() ->
                               {ok, R} = br_query:list_teams(#{state => <<"RJ">>,
                                                               limit => 100}),
                               R
                       end),
    bdd:then("the big four of Rio should be there",
             fun() ->
                     Ids = [maps:get(team, T) || T <- maps:get(teams, Teams)],
                     lists:foreach(fun(Id) -> ?assert(lists:member(Id, Ids)) end,
                                   [<<"flamengo">>, <<"fluminense">>, <<"botafogo">>,
                                    <<"vasco">>])
             end),
    bdd:'and'("no team from another state should be included",
              fun() ->
                      lists:foreach(fun(T) -> ?assertEqual(<<"RJ">>, maps:get(state, T)) end,
                                    maps:get(teams, Teams))
              end).
