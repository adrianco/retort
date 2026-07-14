-module(bsmcp_format_tests).
-include_lib("eunit/include/eunit.hrl").

m() ->
    #{competition => <<"Brasileirão"/utf8>>,
      home => <<"Flamengo">>, away => <<"Fluminense">>,
      home_norm => <<"flamengo">>, away_norm => <<"fluminense">>,
      home_goal => 2, away_goal => 1,
      season => 2023, round => <<"22">>,
      date => <<"2023-09-03">>, stage => undefined}.

contains(Hay, Needle) ->
    binary:match(Hay, Needle) =/= nomatch.

match_line_test() ->
    Line = bsmcp_format:match_line(m()),
    ?assertEqual(<<"2023-09-03: Flamengo 2-1 Fluminense (Brasileirão, Round 22)"/utf8>>, Line).

match_line_unknown_score_test() ->
    M = (m())#{home_goal => undefined, away_goal => undefined},
    Line = bsmcp_format:match_line(M),
    ?assert(contains(Line, <<"Flamengo vs Fluminense">>)).

format_matches_includes_count_test() ->
    Out = bsmcp_format:matches([m(), m()]),
    ?assert(contains(Out, <<"2 match">>)).

format_matches_empty_test() ->
    Out = bsmcp_format:matches([]),
    ?assert(contains(Out, <<"No matches">>)).

format_record_test() ->
    Rec = #{matches => 19, wins => 11, draws => 5, losses => 3,
            goals_for => 28, goals_against => 15, win_rate => 57.9},
    Out = bsmcp_format:team_record(<<"Corinthians">>, Rec),
    ?assert(contains(Out, <<"Corinthians">>)),
    ?assert(contains(Out, <<"Wins: 11">>)),
    ?assert(contains(Out, <<"57.9%">>)).

format_matches_plural_word_test() ->
    Out = bsmcp_format:matches([m(), m()]),
    ?assert(contains(Out, <<"2 matches found">>)).

format_players_plural_word_test() ->
    P = #{name => <<"X">>, nationality => <<"Brazil">>, club => <<"Y">>,
          position => <<"ST">>, overall => 80, potential => 80, age => 25,
          jersey => <<"9">>},
    Out = bsmcp_format:players([P, P]),
    ?assert(contains(Out, <<"2 players found">>)),
    ?assertEqual(nomatch, binary:match(Out, <<"playeres">>)).

format_singular_word_test() ->
    Out = bsmcp_format:matches([m()]),
    ?assert(contains(Out, <<"1 match found">>)).

format_player_test() ->
    P = #{name => <<"Neymar Jr">>, nationality => <<"Brazil">>,
          club => <<"Paris Saint-Germain">>, position => <<"LW">>,
          overall => 92, potential => 92, age => 27, jersey => <<"10">>},
    Out = bsmcp_format:players([P]),
    ?assert(contains(Out, <<"Neymar Jr">>)),
    ?assert(contains(Out, <<"92">>)),
    ?assert(contains(Out, <<"LW">>)).

format_standings_test() ->
    S = [#{team => <<"Flamengo">>, points => 90, wins => 28, draws => 6,
           losses => 4, goals_for => 86, goals_against => 37,
           goal_diff => 49, played => 38}],
    Out = bsmcp_format:standings(<<"Brasileirão"/utf8>>, 2019, S),
    ?assert(contains(Out, <<"Flamengo">>)),
    ?assert(contains(Out, <<"90">>)),
    ?assert(contains(Out, <<"2019">>)).
