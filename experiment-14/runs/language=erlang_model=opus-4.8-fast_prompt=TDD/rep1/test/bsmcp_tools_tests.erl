-module(bsmcp_tools_tests).
-include_lib("eunit/include/eunit.hrl").

m(Comp, Home, Away, HG, AG, Season) ->
    #{competition => Comp, home => Home, away => Away,
      home_norm => bsmcp_normalize:normalize(Home),
      away_norm => bsmcp_normalize:normalize(Away),
      home_goal => HG, away_goal => AG, season => Season,
      round => undefined, date => <<"2019-06-01">>, stage => undefined}.

p(Name, Nat, Club, Pos, Overall) ->
    #{name => Name, name_norm => bsmcp_normalize:normalize(Name),
      nationality => Nat, nationality_norm => bsmcp_normalize:normalize(Nat),
      club => Club, club_norm => bsmcp_normalize:normalize(Club),
      position => Pos, overall => Overall, age => 25, potential => Overall,
      id => <<"1">>, jersey => <<"9">>}.

store() ->
    #{matches =>
          [m(<<"Brasileirão"/utf8>>, <<"Flamengo">>, <<"Santos">>, 2, 0, 2019),
           m(<<"Brasileirão"/utf8>>, <<"Santos">>, <<"Flamengo">>, 1, 1, 2019),
           m(<<"Brasileirão"/utf8>>, <<"Palmeiras">>, <<"Santos">>, 3, 1, 2019)],
      players =>
          [p(<<"Neymar Jr">>, <<"Brazil">>, <<"Santos">>, <<"LW">>, 92),
           p(<<"L. Messi">>, <<"Argentina">>, <<"Barcelona">>, <<"RF">>, 94)]}.

%% --- listing ----------------------------------------------------------

list_returns_tools_test() ->
    Tools = bsmcp_tools:list(),
    ?assert(length(Tools) >= 6),
    Names = [maps:get(name, T) || T <- Tools],
    ?assert(lists:member(<<"find_matches">>, Names)),
    ?assert(lists:member(<<"find_players">>, Names)),
    ?assert(lists:member(<<"standings">>, Names)).

tool_has_schema_test() ->
    [T | _] = bsmcp_tools:list(),
    ?assert(maps:is_key(description, T)),
    ?assert(maps:is_key(inputSchema, T)).

%% --- find_matches -----------------------------------------------------

call_find_matches_test() ->
    {ok, Text} = bsmcp_tools:call(<<"find_matches">>, #{<<"team">> => <<"Flamengo">>}, store()),
    ?assert(binary:match(Text, <<"Flamengo">>) =/= nomatch),
    ?assert(binary:match(Text, <<"2 match">>) =/= nomatch).

call_find_matches_limit_test() ->
    {ok, Text} = bsmcp_tools:call(<<"find_matches">>,
                                  #{<<"team">> => <<"Santos">>, <<"limit">> => 1}, store()),
    ?assert(binary:match(Text, <<"Showing">>) =/= nomatch).

%% --- head_to_head -----------------------------------------------------

call_head_to_head_test() ->
    {ok, Text} = bsmcp_tools:call(<<"head_to_head">>,
                                  #{<<"team_a">> => <<"Flamengo">>,
                                    <<"team_b">> => <<"Santos">>}, store()),
    ?assert(binary:match(Text, <<"head-to-head">>) =/= nomatch).

%% --- team_record ------------------------------------------------------

call_team_record_test() ->
    {ok, Text} = bsmcp_tools:call(<<"team_record">>,
                                  #{<<"team">> => <<"Flamengo">>}, store()),
    ?assert(binary:match(Text, <<"Win rate">>) =/= nomatch).

%% --- find_players -----------------------------------------------------

call_find_players_test() ->
    {ok, Text} = bsmcp_tools:call(<<"find_players">>,
                                  #{<<"nationality">> => <<"Brazil">>}, store()),
    ?assert(binary:match(Text, <<"Neymar Jr">>) =/= nomatch).

%% --- standings --------------------------------------------------------

call_standings_test() ->
    {ok, Text} = bsmcp_tools:call(<<"standings">>,
                                  #{<<"competition">> => <<"Brasileirão"/utf8>>,
                                    <<"season">> => 2019}, store()),
    ?assert(binary:match(Text, <<"standings">>) =/= nomatch).

%% --- statistics -------------------------------------------------------

call_statistics_test() ->
    {ok, Text} = bsmcp_tools:call(<<"match_statistics">>,
                                  #{<<"competition">> => <<"Brasileirão"/utf8>>,
                                    <<"season">> => 2019}, store()),
    ?assert(binary:match(Text, <<"goals per match">>) =/= nomatch).

%% --- error handling ---------------------------------------------------

call_unknown_tool_test() ->
    ?assertMatch({error, _}, bsmcp_tools:call(<<"nope">>, #{}, store())).

call_missing_required_arg_test() ->
    ?assertMatch({error, _}, bsmcp_tools:call(<<"head_to_head">>, #{}, store())).
