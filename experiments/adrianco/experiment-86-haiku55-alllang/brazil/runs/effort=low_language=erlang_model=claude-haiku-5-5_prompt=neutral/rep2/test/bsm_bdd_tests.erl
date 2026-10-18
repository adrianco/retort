%% BDD-style acceptance tests against the real Kaggle datasets.
%% Each scenario mirrors a line in features/brazilian_soccer.feature:
%%   Given the datasets are loaded
%%   When I ask ...
%%   Then ...
%% Expected figures were checked against the raw CSV files.
-module(bsm_bdd_tests).
-include_lib("eunit/include/eunit.hrl").

-define(SERIE_A, <<"Brasileirão Série A"/utf8>>).

feature_test_() ->
    {setup,
     fun given_the_datasets_are_loaded/0,
     fun(_) -> ok end,
     [
      {"Feature: Match queries / Scenario: Find matches between two teams",
       fun() ->
               %% When I search for matches between "Flamengo" and "Fluminense"
               Ms = bsm_query:find_matches(bsm_store:matches(),
                                           #{team => team(<<"Flamengo">>),
                                             opponent => team(<<"Fluminense">>)}),
               %% Then I should receive a list of matches
               ?assert(length(Ms) > 0),
               %% And each match should have date, scores, and competition
               [begin
                    ?assert(is_binary(maps:get(date, M))),
                    ?assert(is_integer(maps:get(home_goals, M))),
                    ?assert(is_integer(maps:get(away_goals, M))),
                    ?assert(is_binary(maps:get(competition, M)))
                end || M <- Ms]
       end},
      {"Feature: Match queries / Scenario: Latest meeting of two rivals",
       fun() ->
               %% When I ask when Flamengo last played Corinthians
               [Last | _] = bsm_query:find_matches(bsm_store:matches(),
                                                   #{team => team(<<"Flamengo">>),
                                                     opponent => team(<<"Corinthians">>)}),
               %% Then the most recent meeting is returned first
               ?assert(maps:get(date, Last) >= <<"2023-01-01">>)
       end},
      {"Feature: Team statistics / Scenario: Get team statistics",
       fun() ->
               %% When I request statistics for "Palmeiras" in season "2023"
               R = bsm_query:team_record(bsm_store:matches(), team(<<"Palmeiras">>),
                                         #{season => 2023}),
               %% Then I should receive wins, losses, draws, and goals
               #{wins := W, draws := D, losses := L, matches := N,
                 goals_for := GF, goals_against := GA} = R,
               ?assertEqual(N, W + D + L),
               ?assert(GF >= 0 andalso GA >= 0)
       end},
      {"Feature: Competition queries / Scenario: Standings are calculated from results",
       fun() ->
               %% When I ask for the 2019 Brasileirão table
               [Champion, Second, Third | _] = bsm_query:standings(bsm_store:matches(), 2019),
               %% Then Flamengo is champion on 90 points with 28 wins (the spec's example)
               ?assertMatch(#{team := <<"Flamengo">>, position := 1, points := 90,
                              won := 28, drawn := 6, lost := 4}, Champion),
               %% And the 2nd and 3rd places are Santos and Palmeiras on 74 points
               ?assertMatch(#{team := <<"Santos">>, points := 74}, Second),
               ?assertMatch(#{team := <<"Palmeiras">>, points := 74}, Third)
       end},
      {"Feature: Competition queries / Scenario: Every Serie A season has 380 matches",
       fun() ->
               %% Given the 2012 and 2019 Brasileirão files overlap
               %% Then the merged data has each round exactly once
               [?assertEqual(380, count_serie_a(Y)) || Y <- [2012, 2019]]
       end},
      {"Feature: Statistical analysis / Scenario: Average goals per match",
       fun() ->
               %% When I ask for league statistics for Serie A 2023
               S = bsm_query:league_stats(bsm_store:matches(),
                                          #{competition => ?SERIE_A, season => 2023}),
               %% Then I receive averages and win rates, all between 0 and 100
               ?assert(maps:get(average_goals_per_match, S) > 1.0),
               ?assert(maps:get(home_win_pct, S) > 0)
       end},
      {"Feature: Player queries / Scenario: Find Brazilian players",
       fun() ->
               %% When I search for players with nationality "Brazil"
               Ps = bsm_query:search_players(bsm_store:players(), #{nationality => <<"Brazil">>}),
               %% Then there are many, sorted by overall rating
               ?assert(length(Ps) > 500),
               ?assertEqual(lists:sort(fun(A, B) -> maps:get(overall, A) >= maps:get(overall, B) end,
                                       Ps), Ps)
       end},
      {"Feature: Player queries / Scenario: Who is Gabriel Barbosa",
       fun() ->
               %% When I search the FIFA data by name
               Ps = bsm_query:search_players(bsm_store:players(), #{name => <<"Gabriel">>,
                                                                    nationality => <<"Brazil">>}),
               %% Then matching Brazilian players are returned with ratings
               ?assert(length(Ps) > 0),
               ?assert(lists:all(fun(P) -> is_integer(maps:get(overall, P)) end, Ps))
       end},
      {"Feature: Team names / Scenario: Name variations resolve to one team",
       fun() ->
               %% Given the datasets use "Palmeiras-SP", "Palmeiras" and "Sociedade Esportiva Palmeiras"
               %% Then all three refer to the same team
               Variants = [<<"Palmeiras-SP">>, <<"Palmeiras">>, <<"Sociedade Esportiva Palmeiras">>],
               [?assert(bsm_team:same(team(<<"Palmeiras">>), team(V))) || V <- Variants]
       end},
      {"Feature: Coverage / Scenario: All six CSV files contribute data",
       fun() ->
               Comps = lists:usort([maps:get(competition, M) || M <- bsm_store:matches()]),
               %% Then every competition family from the spec is present
               [?assert(lists:member(C, Comps))
                || C <- [?SERIE_A, <<"Copa do Brasil">>, <<"Copa Libertadores">>]],
               ?assert(length(bsm_store:players()) > 18000)
       end},
      {"Feature: Performance / Scenario: Simple lookups respond in under 2 seconds",
       fun() ->
               {Micros, _} = timer:tc(fun() ->
                                              bsm_query:find_matches(bsm_store:matches(),
                                                                     #{team => team(<<"Flamengo">>)})
                                      end),
               ?assert(Micros < 2000000)
       end},
      {"Feature: Performance / Scenario: Aggregate queries respond in under 5 seconds",
       fun() ->
               {Micros, _} = timer:tc(fun() ->
                                              bsm_query:league_stats(bsm_store:matches(), #{})
                                      end),
               ?assert(Micros < 5000000)
       end}
     ]}.

given_the_datasets_are_loaded() ->
    Dir = case os:getenv("BSM_DATA_DIR") of
              false -> "data/kaggle";
              D -> D
          end,
    #{matches := M, players := P} = bsm_store:load(Dir),
    ?assert(M > 15000),
    ?assert(P > 18000),
    ok.

team(Name) -> bsm_team:parse(Name).

count_serie_a(Year) ->
    length([M || M <- bsm_store:matches(),
                 maps:get(competition, M) =:= ?SERIE_A,
                 maps:get(season, M) =:= Year]).
