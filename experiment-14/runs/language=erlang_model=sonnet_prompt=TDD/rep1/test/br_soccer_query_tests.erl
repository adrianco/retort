-module(br_soccer_query_tests).
-include_lib("eunit/include/eunit.hrl").

%% Sample data for testing (no file I/O needed).
sample_brasileirao() ->
    [
        #{<<"datetime">> => <<"2023-04-15 18:00:00">>,
          <<"home_team">> => <<"Flamengo-RJ">>,
          <<"away_team">> => <<"Fluminense-RJ">>,
          <<"home_goal">> => <<"2">>,
          <<"away_goal">> => <<"1">>,
          <<"season">> => <<"2023">>,
          <<"round">> => <<"5">>},
        #{<<"datetime">> => <<"2023-06-20 16:00:00">>,
          <<"home_team">> => <<"Palmeiras-SP">>,
          <<"away_team">> => <<"Flamengo-RJ">>,
          <<"home_goal">> => <<"0">>,
          <<"away_goal">> => <<"0">>,
          <<"season">> => <<"2023">>,
          <<"round">> => <<"12">>},
        #{<<"datetime">> => <<"2022-09-10 20:00:00">>,
          <<"home_team">> => <<"Corinthians-SP">>,
          <<"away_team">> => <<"Palmeiras-SP">>,
          <<"home_goal">> => <<"1">>,
          <<"away_goal">> => <<"3">>,
          <<"season">> => <<"2022">>,
          <<"round">> => <<"25">>}
    ].

sample_players() ->
    [
        #{<<"Name">> => <<"Neymar Jr">>,
          <<"Nationality">> => <<"Brazil">>,
          <<"Overall">> => <<"92">>,
          <<"Club">> => <<"Paris Saint-Germain">>,
          <<"Position">> => <<"LW">>,
          <<"Age">> => <<"26">>},
        #{<<"Name">> => <<"L. Messi">>,
          <<"Nationality">> => <<"Argentina">>,
          <<"Overall">> => <<"94">>,
          <<"Club">> => <<"FC Barcelona">>,
          <<"Position">> => <<"RW">>,
          <<"Age">> => <<"31">>},
        #{<<"Name">> => <<"G. Barbosa">>,
          <<"Nationality">> => <<"Brazil">>,
          <<"Overall">> => <<"78">>,
          <<"Club">> => <<"Flamengo">>,
          <<"Position">> => <<"ST">>,
          <<"Age">> => <<"22">>}
    ].

%% TDD Cycle 1: Match filtering by team
filter_matches_by_team_test() ->
    Matches = sample_brasileirao(),
    Result = br_soccer_query:filter_by_team(Matches, <<"Flamengo">>),
    ?assertEqual(2, length(Result)).

filter_matches_home_team_test() ->
    Matches = sample_brasileirao(),
    Result = br_soccer_query:filter_by_team(Matches, <<"Palmeiras">>),
    ?assertEqual(2, length(Result)).

%% TDD Cycle 2: Filter by season
filter_by_season_test() ->
    Matches = sample_brasileirao(),
    Result = br_soccer_query:filter_by_season(Matches, <<"2023">>),
    ?assertEqual(2, length(Result)).

filter_by_season_empty_test() ->
    Matches = sample_brasileirao(),
    Result = br_soccer_query:filter_by_season(Matches, <<"2020">>),
    ?assertEqual(0, length(Result)).

%% TDD Cycle 3: Head-to-head
head_to_head_test() ->
    Matches = sample_brasileirao(),
    Result = br_soccer_query:head_to_head(Matches, <<"Flamengo">>, <<"Fluminense">>),
    ?assertEqual(1, length(Result)).

head_to_head_symmetric_test() ->
    Matches = sample_brasileirao(),
    R1 = br_soccer_query:head_to_head(Matches, <<"Flamengo">>, <<"Fluminense">>),
    R2 = br_soccer_query:head_to_head(Matches, <<"Fluminense">>, <<"Flamengo">>),
    ?assertEqual(length(R1), length(R2)).

%% TDD Cycle 4: Team statistics
team_stats_test() ->
    Matches = sample_brasileirao(),
    Stats = br_soccer_query:team_stats(Matches, <<"Flamengo">>),
    ?assertEqual(2, maps:get(matches, Stats)),
    ?assertEqual(1, maps:get(wins, Stats)),
    ?assertEqual(1, maps:get(draws, Stats)),
    ?assertEqual(0, maps:get(losses, Stats)),
    ?assertEqual(2, maps:get(goals_for, Stats)),
    ?assertEqual(1, maps:get(goals_against, Stats)).

%% TDD Cycle 5: Player search
search_players_by_name_test() ->
    Players = sample_players(),
    Result = br_soccer_query:search_players(Players, #{name => <<"Neymar">>}),
    ?assertEqual(1, length(Result)),
    ?assertEqual(<<"Neymar Jr">>, maps:get(<<"Name">>, hd(Result))).

search_players_by_nationality_test() ->
    Players = sample_players(),
    Result = br_soccer_query:search_players(Players, #{nationality => <<"Brazil">>}),
    ?assertEqual(2, length(Result)).

search_players_by_club_test() ->
    Players = sample_players(),
    Result = br_soccer_query:search_players(Players, #{club => <<"Flamengo">>}),
    ?assertEqual(1, length(Result)).

%% TDD Cycle 6: Standings calculation
standings_test() ->
    Matches = sample_brasileirao(),
    Standings = br_soccer_query:compute_standings(Matches),
    %% Palmeiras-SP: 1 win (vs Corinthians as away) + 1 draw => 4 pts
    %% Raw names are used in standings so the key retains the state suffix.
    Palmeiras = lists:keyfind(<<"Palmeiras-SP">>, 1, Standings),
    ?assertMatch({<<"Palmeiras-SP">>, #{points := 4}}, Palmeiras).

%% TDD Cycle 7: Biggest matches
biggest_matches_test() ->
    Matches = sample_brasileirao(),
    Result = br_soccer_query:biggest_matches(Matches, 3),
    %% Corinthians 1-3 Palmeiras has diff 2, biggest first
    [{_Date, Home, Away, HG, AG} | _] = Result,
    ?assertEqual(2, abs(HG - AG)),
    _ = Home, _ = Away.

%% TDD Cycle 8: Goals per match average
avg_goals_test() ->
    Matches = sample_brasileirao(),
    Avg = br_soccer_query:avg_goals(Matches),
    %% (3 + 0 + 4) / 3 = 7/3 ≈ 2.33
    ?assert(abs(Avg - 2.333) < 0.01).
