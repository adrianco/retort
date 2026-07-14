-module(bsmcp_query2_tests).
-include_lib("eunit/include/eunit.hrl").

m(Comp, Home, Away, HG, AG, Season) ->
    #{competition => Comp, home => Home, away => Away,
      home_norm => bsmcp_normalize:normalize(Home),
      away_norm => bsmcp_normalize:normalize(Away),
      home_goal => HG, away_goal => AG,
      season => Season, round => undefined,
      date => <<"2019-01-01">>, stage => undefined}.

p(Name, Nat, Club, Pos, Overall) ->
    #{name => Name, name_norm => bsmcp_normalize:normalize(Name),
      nationality => Nat, nationality_norm => bsmcp_normalize:normalize(Nat),
      club => Club, club_norm => bsmcp_normalize:normalize(Club),
      position => Pos, overall => Overall, age => 25,
      potential => Overall, id => <<"1">>, jersey => <<"10">>}.

players() ->
    [p(<<"Neymar Jr">>, <<"Brazil">>, <<"Paris Saint-Germain">>, <<"LW">>, 92),
     p(<<"Alisson">>, <<"Brazil">>, <<"Liverpool">>, <<"GK">>, 89),
     p(<<"Gabriel Barbosa">>, <<"Brazil">>, <<"Flamengo">>, <<"ST">>, 80),
     p(<<"Bruno Henrique">>, <<"Brazil">>, <<"Flamengo">>, <<"LW">>, 78),
     p(<<"L. Messi">>, <<"Argentina">>, <<"FC Barcelona">>, <<"RF">>, 94)].

%% --- player search ----------------------------------------------------

find_player_by_name_substring_test() ->
    R = bsmcp_query:find_players(players(), #{name => <<"gabriel">>}),
    ?assertEqual(1, length(R)),
    ?assertEqual(<<"Gabriel Barbosa">>, maps:get(name, hd(R))).

find_players_by_nationality_test() ->
    R = bsmcp_query:find_players(players(), #{nationality => <<"Brazil">>}),
    ?assertEqual(4, length(R)).

find_players_by_club_test() ->
    R = bsmcp_query:find_players(players(), #{club => <<"Flamengo">>}),
    ?assertEqual(2, length(R)).

find_players_by_position_test() ->
    R = bsmcp_query:find_players(players(), #{position => <<"LW">>}),
    ?assertEqual(2, length(R)).

find_players_sorted_by_overall_desc_test() ->
    R = bsmcp_query:find_players(players(), #{nationality => <<"Brazil">>}),
    Overalls = [maps:get(overall, P) || P <- R],
    ?assertEqual([92, 89, 80, 78], Overalls).

top_players_limit_test() ->
    R = bsmcp_query:top_players(players(), #{nationality => <<"Brazil">>}, 2),
    ?assertEqual(2, length(R)),
    ?assertEqual(<<"Neymar Jr">>, maps:get(name, hd(R))).

find_players_min_overall_test() ->
    R = bsmcp_query:find_players(players(), #{min_overall => 89}),
    ?assertEqual(3, length(R)).

%% --- standings --------------------------------------------------------

standings_matches() ->
    [m(<<"Brasileirão"/utf8>>, <<"Flamengo">>, <<"Santos">>, 2, 0, 2019),
     m(<<"Brasileirão"/utf8>>, <<"Santos">>, <<"Palmeiras">>, 1, 1, 2019),
     m(<<"Brasileirão"/utf8>>, <<"Palmeiras">>, <<"Flamengo">>, 0, 3, 2019),
     m(<<"Brasileirão"/utf8>>, <<"Flamengo">>, <<"Palmeiras">>, 1, 1, 2019),
     m(<<"Copa do Brasil"/utf8>>, <<"Flamengo">>, <<"Santos">>, 5, 0, 2019)].

standings_points_test() ->
    S = bsmcp_query:standings(standings_matches(), <<"Brasileirão"/utf8>>, 2019),
    Flamengo = hd(S),
    %% Flamengo Brasileirão: W(2-0) W(3-0) D(1-1) = 7 pts, played 3
    ?assertEqual(<<"Flamengo">>, maps:get(team, Flamengo)),
    ?assertEqual(7, maps:get(points, Flamengo)),
    ?assertEqual(3, maps:get(played, Flamengo)),
    ?assertEqual(2, maps:get(wins, Flamengo)).

standings_excludes_other_competition_test() ->
    S = bsmcp_query:standings(standings_matches(), <<"Brasileirão"/utf8>>, 2019),
    Flamengo = hd(S),
    %% The 5-0 Copa do Brasil game must not count: GF should be 2+3+1 = 6
    ?assertEqual(6, maps:get(goals_for, Flamengo)).

standings_uses_stored_norm_key_test() ->
    %% Two clubs whose display names are identical after suffix stripping
    %% ("Atletico") but whose stored norm keys differ must stay as two rows.
    MG = #{competition => <<"Brasileirão"/utf8>>,
           home => <<"Atletico">>, away => <<"Flamengo">>,
           home_norm => <<"atletico-mg">>, away_norm => <<"flamengo">>,
           home_goal => 2, away_goal => 0, season => 2019,
           round => undefined, date => <<"2019-05-01">>, stage => undefined},
    PR = #{competition => <<"Brasileirão"/utf8>>,
           home => <<"Atletico">>, away => <<"Santos">>,
           home_norm => <<"athletico-pr">>, away_norm => <<"santos">>,
           home_goal => 1, away_goal => 0, season => 2019,
           round => undefined, date => <<"2019-05-08">>, stage => undefined},
    S = bsmcp_query:standings([MG, PR], <<"Brasileirão"/utf8>>, 2019),
    Atleticos = [R || R <- S, maps:get(team, R) =:= <<"Atletico">>],
    ?assertEqual(2, length(Atleticos)).

standings_ordering_test() ->
    S = bsmcp_query:standings(standings_matches(), <<"Brasileirão"/utf8>>, 2019),
    Teams = [maps:get(team, X) || X <- S],
    ?assertEqual([<<"Flamengo">>, <<"Palmeiras">>, <<"Santos">>], Teams).

%% --- statistics -------------------------------------------------------

avg_goals_test() ->
    Ms = [m(<<"X">>, <<"A">>, <<"B">>, 2, 1, 2019),
          m(<<"X">>, <<"C">>, <<"D">>, 0, 0, 2019),
          m(<<"X">>, <<"E">>, <<"F">>, 3, 2, 2019)],
    %% (3 + 0 + 5) / 3 = 2.67
    ?assertEqual(2.67, bsmcp_query:avg_goals(Ms)).

home_win_rate_test() ->
    Ms = [m(<<"X">>, <<"A">>, <<"B">>, 2, 1, 2019),
          m(<<"X">>, <<"C">>, <<"D">>, 0, 0, 2019),
          m(<<"X">>, <<"E">>, <<"F">>, 0, 2, 2019),
          m(<<"X">>, <<"G">>, <<"H">>, 1, 0, 2019)],
    %% 2 home wins of 4 = 50.0
    ?assertEqual(50.0, bsmcp_query:home_win_rate(Ms)).

biggest_wins_test() ->
    Ms = [m(<<"X">>, <<"A">>, <<"B">>, 2, 1, 2019),
          m(<<"X">>, <<"C">>, <<"D">>, 8, 0, 2019),
          m(<<"X">>, <<"E">>, <<"F">>, 5, 0, 2019)],
    R = bsmcp_query:biggest_wins(Ms, 2),
    ?assertEqual(2, length(R)),
    ?assertEqual(<<"C">>, maps:get(home, hd(R))).
