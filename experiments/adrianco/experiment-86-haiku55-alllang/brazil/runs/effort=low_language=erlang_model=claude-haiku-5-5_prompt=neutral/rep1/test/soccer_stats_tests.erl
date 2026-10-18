%% Feature: match, team, standings, player and aggregate queries
-module(soccer_stats_tests).
-include_lib("eunit/include/eunit.hrl").

%% Fixture: a small in-memory dataset built the same way the loader builds it.
match(Date, Home, HG, Away, AG, Season, Comp) ->
    #{source => test, date => Date, season => Season, competition => Comp,
      stage => <<"Round 1">>, round => 1,
      home => Home, away => Away,
      home_tokens => soccer_util:tokens(Home), away_tokens => soccer_util:tokens(Away),
      home_goals => HG, away_goals => AG}.

fixtures() ->
    Serie = <<"Brasileirão Série A"/utf8>>,
    [match(20230903, <<"Flamengo">>, 2, <<"Fluminense">>, 1, 2023, Serie),
     match(20230528, <<"Fluminense">>, 1, <<"Flamengo">>, 0, 2023, Serie),
     match(20230610, <<"Sport Club Corinthians Paulista">>, 3, <<"Palmeiras">>, 0, 2023, Serie),
     match(20230612, <<"Palmeiras">>, 2, <<"Sport Club Corinthians Paulista">>, 2, 2023, Serie),
     match(20230701, <<"Palmeiras">>, 1, <<"Santos">>, 1, 2023, Serie),
     match(20220101, <<"Sao Paulo">>, 0, <<"Santos">>, 4, 2022, Serie),
     match(20220201, <<"Santos">>, 5, <<"Sao Paulo">>, 0, 2022, <<"Copa do Brasil">>)].

%% Scenario: find matches between two teams in either orientation
%%   Given a Flamengo vs Fluminense fixture in each home/away direction
%%   When I search for matches between "Flamengo" and "Fluminense"
%%   Then both matches are found, newest first
find_matches_between_teams_test() ->
    Found = soccer_stats:search(fixtures(), #{team => <<"Flamengo">>, opponent => <<"Fluminense">>}),
    ?assertEqual([20230903, 20230528], [maps:get(date, M) || M <- Found]).

%% Scenario: team names match on tokens, ignoring accents and long names
%%   Given Corinthians is listed as "Sport Club Corinthians Paulista"
%%   When I search for "Corinthians" and "São Paulo" with an accent
%%   Then the long name and the unaccented name both match
team_name_variations_test() ->
    Corinthians = soccer_stats:search(fixtures(), #{team => <<"Corinthians">>}),
    ?assertEqual(2, length(Corinthians)),
    SaoPaulo = soccer_stats:search(fixtures(), #{team => <<"São Paulo"/utf8>>}),
    ?assertEqual(2, length(SaoPaulo)).

%% Scenario: team record for a season and venue
%%   Given Palmeiras home games in 2023 (a 2-2 draw and a 1-1 draw)
%%   When I request the home record for Palmeiras in season 2023
%%   Then it reports two draws, three goals scored and a 0% win rate
home_record_test() ->
    R = soccer_stats:record(fixtures(),
                            #{team => <<"Palmeiras">>, season => 2023, venue => home}),
    ?assertEqual(2, maps:get(played, R)),
    ?assertEqual(0, maps:get(wins, R)),
    ?assertEqual(2, maps:get(draws, R)),
    ?assertEqual(3, maps:get(gf, R)),
    ?assertEqual(0.0, maps:get(win_rate, R)).

%% Scenario: league standings from results
%%   Given the 2023 Brasileirão matches
%%   When I calculate the table
%%   Then Corinthians (3-0 and a 2-2 draw) leads with 4 points from 2 games
standings_test() ->
    [First | _] = soccer_stats:standings(fixtures(), 2023, <<"Brasileirão"/utf8>>),
    ?assertEqual(<<"Sport Club Corinthians Paulista">>, maps:get(team, First)),
    ?assertEqual(4, maps:get(points, First)).

%% Scenario: league summary averages
%%   Given the 2022 matches in the Brasileirão
%%   When I compute the summary
%%   Then goals per match and home win rate are calculated
league_summary_test() ->
    S = soccer_stats:league_summary(fixtures(), 2022, <<"Brasileirão"/utf8>>),
    ?assertEqual(1, maps:get(matches, S)),
    ?assertEqual(4.0, maps:get(goals_per_match, S)),
    ?assertEqual(0.0, maps:get(home_win_rate, S)).

%% Scenario: biggest wins
%%   Given decisive matches in the fixtures
%%   When I ask for the biggest win
%%   Then the largest margin comes first
biggest_wins_test() ->
    [Top | _] = soccer_stats:biggest_wins(fixtures(), #{}, 3),
    ?assertEqual(20220201, maps:get(date, Top)).

%% Scenario: player lookup by name and club
%%   Given players with different clubs and overall ratings
%%   When I search for players at "Flamengo" with overall at least 80
%%   Then only Flamengo players are returned, highest rated first
player_search_test() ->
    Players = [player(<<"Gabriel Barbosa">>, <<"CR Flamengo">>, 80, <<"ST">>),
               player(<<"Gabriel Jesus">>, <<"Manchester City">>, 84, <<"ST">>),
               player(<<"Diego">>, <<"Flamengo">>, 82, <<"CAM">>)],
    Hits = soccer_stats:search_players(Players, #{club => <<"Flamengo">>, min_overall => 80}),
    ?assertEqual([<<"Diego">>, <<"Gabriel Barbosa">>], [maps:get(name, P) || P <- Hits]).

%% Scenario: club summary for one nationality
%%   Given Brazilian and non-Brazilian players
%%   When I summarise Brazilian players by club
%%   Then only Brazilian players are counted
club_summary_test() ->
    Players = [player(<<"A">>, <<"Flamengo">>, 80, <<"ST">>),
               player(<<"B">>, <<"Flamengo">>, 70, <<"ST">>),
               (player(<<"C">>, <<"Chelsea">>, 99, <<"ST">>))#{nationality => <<"England">>,
                                                                nationality_tokens => [<<"england">>]}],
    ?assertEqual([{<<"Flamengo">>, 2, 75.0}], soccer_stats:club_summary(Players, <<"Brazil">>)).

player(Name, Club, Overall, Position) ->
    #{name => Name, name_tokens => soccer_util:tokens(Name),
      age => 25, nationality => <<"Brazil">>, nationality_tokens => [<<"brazil">>],
      overall => Overall, potential => Overall, club => Club,
      club_tokens => soccer_util:tokens(Club), position => Position}.
