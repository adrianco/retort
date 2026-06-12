-module(bsmcp_query_tests).
-include_lib("eunit/include/eunit.hrl").

%% Build a canonical match map for fixtures.
m(Comp, Home, Away, HG, AG, Season, Date) ->
    #{competition => Comp,
      home => Home, away => Away,
      home_norm => bsmcp_normalize:normalize(Home),
      away_norm => bsmcp_normalize:normalize(Away),
      home_goal => HG, away_goal => AG,
      season => Season, round => undefined,
      date => Date, stage => undefined}.

matches() ->
    [m(<<"Brasileirão"/utf8>>, <<"Flamengo">>, <<"Fluminense">>, 2, 1, 2023, <<"2023-09-03">>),
     m(<<"Brasileirão"/utf8>>, <<"Fluminense">>, <<"Flamengo">>, 1, 0, 2023, <<"2023-05-28">>),
     m(<<"Brasileirão"/utf8>>, <<"Flamengo">>, <<"Palmeiras">>, 3, 0, 2023, <<"2023-07-01">>),
     m(<<"Brasileirão"/utf8>>, <<"Palmeiras">>, <<"Flamengo">>, 1, 1, 2022, <<"2022-07-01">>),
     m(<<"Copa do Brasil"/utf8>>, <<"Flamengo">>, <<"Fluminense">>, 0, 0, 2022, <<"2022-04-10">>)].

%% --- find_matches -----------------------------------------------------

find_by_team_either_side_test() ->
    R = bsmcp_query:find_matches(matches(), #{team => <<"Fluminense">>}),
    ?assertEqual(3, length(R)).

find_by_team_with_suffix_test() ->
    %% "Flamengo-RJ" should match "Flamengo" via normalization
    R = bsmcp_query:find_matches(matches(), #{team => <<"Flamengo-RJ">>}),
    ?assertEqual(5, length(R)).

find_by_two_teams_test() ->
    R = bsmcp_query:find_matches(matches(),
                                 #{team => <<"Flamengo">>, opponent => <<"Fluminense">>}),
    ?assertEqual(3, length(R)).

find_by_season_test() ->
    R = bsmcp_query:find_matches(matches(), #{season => 2022}),
    ?assertEqual(2, length(R)).

find_by_competition_test() ->
    R = bsmcp_query:find_matches(matches(), #{competition => <<"Copa do Brasil"/utf8>>}),
    ?assertEqual(1, length(R)).

find_by_home_team_test() ->
    R = bsmcp_query:find_matches(matches(), #{home_team => <<"Flamengo">>}),
    ?assertEqual(3, length(R)).

find_combined_filters_test() ->
    R = bsmcp_query:find_matches(matches(),
                                 #{team => <<"Flamengo">>, season => 2023,
                                   competition => <<"Brasileirão"/utf8>>}),
    ?assertEqual(3, length(R)).

%% --- head_to_head -----------------------------------------------------

head_to_head_test() ->
    {Ms, Rec} = bsmcp_query:head_to_head(matches(), <<"Flamengo">>, <<"Fluminense">>),
    ?assertEqual(3, length(Ms)),
    %% Flamengo: won 2-1, lost 0-1 (away), drew 0-0 -> 1 win, 1 loss, 1 draw
    ?assertEqual(1, maps:get(a_wins, Rec)),
    ?assertEqual(1, maps:get(b_wins, Rec)),
    ?assertEqual(1, maps:get(draws, Rec)).

%% --- team_record ------------------------------------------------------

team_record_test() ->
    Rec = bsmcp_query:team_record(matches(), <<"Flamengo">>, #{}),
    %% Flamengo matches: W(2-1), L(0-1), W(3-0), D(1-1), D(0-0) = 2W 2D 1L
    ?assertEqual(5, maps:get(matches, Rec)),
    ?assertEqual(2, maps:get(wins, Rec)),
    ?assertEqual(2, maps:get(draws, Rec)),
    ?assertEqual(1, maps:get(losses, Rec)),
    ?assertEqual(6, maps:get(goals_for, Rec)),
    ?assertEqual(3, maps:get(goals_against, Rec)).

team_record_home_only_test() ->
    Rec = bsmcp_query:team_record(matches(), <<"Flamengo">>, #{home_only => true}),
    %% Home matches for Flamengo: 2-1, 3-0, 0-0 = 2W 1D
    ?assertEqual(3, maps:get(matches, Rec)),
    ?assertEqual(2, maps:get(wins, Rec)),
    ?assertEqual(1, maps:get(draws, Rec)),
    ?assertEqual(0, maps:get(losses, Rec)).

team_record_filtered_by_season_test() ->
    Rec = bsmcp_query:team_record(matches(), <<"Flamengo">>,
                                  #{season => 2023, competition => <<"Brasileirão"/utf8>>}),
    ?assertEqual(3, maps:get(matches, Rec)).

win_rate_test() ->
    Rec = bsmcp_query:team_record(matches(), <<"Flamengo">>, #{}),
    %% 2 wins / 5 = 40.0
    ?assertEqual(40.0, maps:get(win_rate, Rec)).
