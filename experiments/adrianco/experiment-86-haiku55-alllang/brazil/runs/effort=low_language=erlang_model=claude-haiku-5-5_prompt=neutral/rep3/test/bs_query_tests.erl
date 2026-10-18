%%% Feature: Questions about matches, teams, competitions and players are answered from the data.
-module(bs_query_tests).

-include_lib("eunit/include/eunit.hrl").
-import(bs_test_support, [u/1]).

-define(SERIE_A, u("Brasileirão Série A")).

query_test_() ->
    {setup, fun bs_test_support:fixture_data/0, fun(_) -> ok end,
     fun(D) ->
         [{"Given Flamengo-RJ, When resolving the free-text name, Then the club key is found",
           ?_assertEqual({ok, <<"flamengo">>}, bs_query:resolve_team(<<"Flamengo-RJ">>, D))},

          {"Given a state code, When resolving a shared name, Then the matching club is chosen",
           ?_assertEqual({ok, <<"atletico-pr">>}, bs_query:resolve_team(<<"Atletico-PR">>, D))},

          {"Given an unknown team, When resolving, Then not_found is returned",
           ?_assertEqual({error, not_found}, bs_query:resolve_team(<<"Nowhere FC">>, D))},

          {"Given Flamengo in 2019 Série A, When asked for team stats, Then record is W-L with splits",
           ?_test(begin
                      S = bs_query:team_stats(D, <<"flamengo">>,
                                              #{season => 2019, competition => ?SERIE_A}),
                      ?assertEqual({2, 1, 0, 1}, {maps:get(matches, S), maps:get(wins, S),
                                                  maps:get(draws, S), maps:get(losses, S)}),
                      ?assertEqual({4, 3}, {maps:get(goals_for, S), maps:get(goals_against, S)}),
                      ?assertEqual(50.0, maps:get(win_rate, S)),
                      ?assertEqual(1, maps:get(wins, maps:get(home, S))),
                      ?assertEqual(1, maps:get(losses, maps:get(away, S)))
                  end)},

          {"Given Flamengo and Cruzeiro, When asked head-to-head, Then the record is returned",
           ?_test(begin
                      H = bs_query:head_to_head(D, <<"flamengo">>, <<"cruzeiro">>),
                      ?assertEqual(1, length(maps:get(matches, H))),
                      ?assertEqual({1, 0, 0}, {maps:get(team1_wins, H), maps:get(team2_wins, H),
                                               maps:get(draws, H)})
                  end)},

          {"Given the 2019 Série A, When the table is calculated, Then points order the teams",
           ?_test(begin
                      [Top | _] = Table = bs_query:standings(D, #{season => 2019,
                                                                  competition => ?SERIE_A}),
                      ?assertEqual({<<"Palmeiras">>, 4}, {maps:get(team, Top), maps:get(points, Top)}),
                      Flamengo = hd([R || R <- Table, maps:get(key, R) =:= <<"flamengo">>]),
                      ?assertEqual(3, maps:get(points, Flamengo))
                  end)},

          {"Given the 2019 Série A, When averaging goals, Then the mean over 7 matches is returned",
           ?_assertEqual(#{matches => 7, average_goals => 2.71},
                         bs_query:aggregate(D, {average_goals,
                                                #{season => 2019, competition => ?SERIE_A}}))},

          {"Given the 2019 Série A, When asked for home win rate, Then 3 of 7 is 42.9%",
           ?_assertEqual(42.9,
                         maps:get(home_win_rate,
                                  bs_query:aggregate(D, {home_win_rate,
                                                         #{season => 2019,
                                                           competition => ?SERIE_A}})))},

          {"Given Flamengo, When listing matches, Then the newest comes first",
           ?_assertEqual(<<"2019-06-04">>,
                         maps:get(date, hd(bs_query:search_matches(D, #{team => <<"flamengo">>}))))},

          {"Given a date range, When listing matches, Then only matches within it are returned",
           ?_assertEqual(2, length(bs_query:search_matches(
                                     D, #{team => <<"flamengo">>, from => <<"2019-05-01">>,
                                          to => <<"2019-05-31">>})))},

          {"Given Brazil as nationality, When searching players, Then they are sorted by rating",
           ?_assertEqual([<<"Casemiro">>, <<"Gabriel Jesus">>, <<"Thiago Morales">>, <<"Pedro Ruiz">>],
                         [maps:get(name, P) || P <- bs_query:search_players(
                                                     D, #{nationality => <<"brazil">>})])},

          {"Given a partial name, When searching players, Then accents and case are ignored",
           ?_assertEqual([<<"Gabriel Jesus">>],
                         [maps:get(name, P) || P <- bs_query:search_players(
                                                     D, #{name => <<"GABRIEL">>})])},

          {"Given Brazilian players at Brazilian clubs, When summarised, Then only those clubs appear",
           ?_assertEqual([#{club => <<"Sport Club do Recife">>, players => 2,
                            average_overall => 72.0}],
                         bs_query:brazilian_club_summary(D))}]
     end}.
