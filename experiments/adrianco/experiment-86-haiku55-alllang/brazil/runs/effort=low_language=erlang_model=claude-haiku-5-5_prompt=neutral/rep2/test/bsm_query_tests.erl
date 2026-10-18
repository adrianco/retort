%% Query and statistics tests over a small hand-built fixture, so every expected
%% number can be checked by reading the fixture below.
-module(bsm_query_tests).
-include_lib("eunit/include/eunit.hrl").

%% Fixture (scores are home-away):
%%   2023 Serie A:  Flamengo 2-1 Fluminense, Fluminense 1-0 Flamengo,
%%                  Palmeiras 3-0 Flamengo, Flamengo 0-0 Palmeiras
%%   2023 Cup:      Flamengo 1-1 Fluminense
%%   2019 Serie A:  Flamengo 4-0 Santos, Santos 0-0 Flamengo,
%%                  Atletico-MG 2-2 Santos, Atletico-PR 1-0 Santos
m(Date, Comp, H, A, HG, AG) ->
    #{date => Date, season => binary_to_integer(binary:part(Date, 0, 4)),
      competition => Comp, stage => <<>>,
      home => bsm_team:parse(H), away => bsm_team:parse(A),
      home_goals => HG, away_goals => AG}.

serie_a() -> <<"Brasileirão Série A"/utf8>>.
cup() -> <<"Copa do Brasil">>.

fixture() ->
    [m(<<"2023-03-01">>, serie_a(), <<"Flamengo-RJ">>, <<"Fluminense-RJ">>, 2, 1),
     m(<<"2023-04-01">>, serie_a(), <<"Fluminense-RJ">>, <<"Flamengo-RJ">>, 1, 0),
     m(<<"2023-05-01">>, serie_a(), <<"Palmeiras-SP">>, <<"Flamengo-RJ">>, 3, 0),
     m(<<"2023-06-01">>, serie_a(), <<"Flamengo-RJ">>, <<"Palmeiras-SP">>, 0, 0),
     m(<<"2023-07-01">>, cup(), <<"Flamengo">>, <<"Fluminense">>, 1, 1),
     m(<<"2019-07-01">>, serie_a(), <<"Flamengo-RJ">>, <<"Santos-SP">>, 4, 0),
     m(<<"2019-08-01">>, serie_a(), <<"Santos-SP">>, <<"Flamengo-RJ">>, 0, 0),
     m(<<"2019-09-01">>, serie_a(), <<"Atletico-MG">>, <<"Santos-SP">>, 2, 2),
     m(<<"2019-09-02">>, serie_a(), <<"Atletico-PR">>, <<"Santos-SP">>, 1, 0)].

flamengo() -> bsm_team:parse(<<"Flamengo">>).
fluminense() -> bsm_team:parse(<<"Fluminense">>).

dates(Ms) -> [maps:get(date, M) || M <- Ms].

find_matches_test_() ->
    [
     {"team alone returns home and away matches, newest first",
      ?_assertEqual([<<"2023-07-01">>, <<"2023-06-01">>, <<"2023-05-01">>, <<"2023-04-01">>,
                     <<"2023-03-01">>, <<"2019-08-01">>, <<"2019-07-01">>],
                    dates(bsm_query:find_matches(fixture(), #{team => flamengo()})))},
     {"team and opponent return only matches between the two",
      ?_assertEqual(3, length(bsm_query:find_matches(fixture(),
                                                     #{team => flamengo(), opponent => fluminense()})))},
     {"season restricts results",
      ?_assertEqual(5, length(bsm_query:find_matches(fixture(), #{team => flamengo(), season => 2023})))},
     {"competition is a case-insensitive substring",
      ?_assertEqual(1, length(bsm_query:find_matches(fixture(), #{competition => <<"copa do brasil">>})))},
     {"date range is inclusive",
      ?_assertEqual(2, length(bsm_query:find_matches(fixture(),
                                                     #{date_from => <<"2023-04-01">>,
                                                       date_to => <<"2023-05-01">>})))},
     {"venue home keeps only games the team hosted",
      ?_assertEqual([<<"2023-06-01">>, <<"2023-03-01">>],
                    dates(bsm_query:find_matches(fixture(),
                                                 #{team => flamengo(), venue => home,
                                                   competition => serie_a(), season => 2023})))}
    ].

team_record_test_() ->
    [
     {"wins, draws, losses, goals and win rate for a season",
      ?_assertEqual(#{team => <<"Flamengo">>, matches => 4, wins => 1, draws => 1, losses => 2,
                      goals_for => 2, goals_against => 5, goal_difference => -3, win_rate_pct => 25.0},
                    bsm_query:team_record(fixture(), flamengo(),
                                          #{competition => serie_a(), season => 2023}))},
     {"home-only record counts just home games",
      ?_assertMatch(#{matches := 2, wins := 1, draws := 1},
                    bsm_query:team_record(fixture(), flamengo(),
                                          #{competition => serie_a(), season => 2023, venue => home}))},
     {"a team with no matches has zeroed totals",
      ?_assertMatch(#{matches := 0, win_rate_pct := +0.0},
                    bsm_query:team_record(fixture(), bsm_team:parse(<<"Nobody">>), #{}))}
    ].

head_to_head_test_() ->
    [
     {"head-to-head counts wins, draws and goals from the first team's view",
      ?_assertMatch(#{total := 3, team_a_wins := 1, draws := 1, team_b_wins := 1,
                      team_a_goals := 3, team_b_goals := 3},
                    bsm_query:head_to_head(fixture(), flamengo(), fluminense(), #{}))}
    ].

standings_test_() ->
    [
     {"points are 3/1/0 and ranked highest first",
      ?_assertEqual([4, 3, 2, 1],
                    [maps:get(points, R) || R <- bsm_query:standings(fixture(), 2019)])},
     {"the leader is identified by name",
      ?_assertMatch([#{team := <<"Flamengo">>, position := 1, won := 1, drawn := 1} | _],
                    bsm_query:standings(fixture(), 2019))},
     {"only Serie A matches are counted",
      ?_assertEqual([], bsm_query:standings(fixture(), 2010))}
    ].

league_stats_test_() ->
    [
     {"2019 Serie A: averages, percentages and biggest wins",
      ?_test(begin
                 S = bsm_query:league_stats(fixture(), #{competition => serie_a(), season => 2019}),
                 ?assertMatch(#{matches := 4, home_win_pct := 50.0, draw_pct := 50.0,
                                away_win_pct := +0.0}, S),
                 ?assertEqual(2.25, maps:get(average_goals_per_match, S)),
                 %% Wins only, largest margin first: Flamengo 4-0, then Atletico-PR 1-0.
                 ?assertEqual([{4, 0}, {1, 0}], [{maps:get(home_goals, M), maps:get(away_goals, M)}
                                         || M <- maps:get(biggest_wins, S)])
             end)},
     {"an empty result gives zero averages rather than crashing",
      ?_assertMatch(#{matches := 0, average_goals_per_match := +0.0},
                    bsm_query:league_stats(fixture(), #{competition => <<"nothing">>}))}
    ].

search_players_test_() ->
    Players = [#{name => <<"Neymar Jr">>, nationality => <<"Brazil">>,
                 club => <<"Paris Saint-Germain">>, position => <<"LW">>, overall => 92},
               #{name => <<"Alisson">>, nationality => <<"Brazil">>,
                 club => <<"Liverpool">>, position => <<"GK">>, overall => 89},
               #{name => <<"Messi">>, nationality => <<"Argentina">>,
                 club => <<"FC Barcelona">>, position => <<"RF">>, overall => 94}],
    [
     {"filters by nationality and sorts by overall, highest first",
      ?_assertEqual([<<"Neymar Jr">>, <<"Alisson">>],
                    [maps:get(name, P) || P <- bsm_query:search_players(
                                                 Players, #{nationality => <<"brazil">>})])},
     {"club fragment and minimum overall combine",
      ?_assertEqual([<<"Neymar Jr">>],
                    [maps:get(name, P) || P <- bsm_query:search_players(
                                                 Players, #{club => <<"saint">>, min_overall => 90})])}
    ].

find_teams_test_() ->
    [
     {"a partial name returns only the matching teams",
      ?_assertEqual([<<"Fluminense">>, <<"Fluminense">>],
                    [maps:get(name, T) || T <- bsm_query:find_teams(fixture(), <<"flu">>)])},
     {"an empty query lists every distinct team (name and state)",
      %% The cup rows carry no state, so they appear as separate entries here.
      %% The loader fills known states, which removes that split for real data.
      ?_assertEqual(8, length(bsm_query:find_teams(fixture(), <<>>)))}
    ].
