%% coding: utf-8
-module(soccer_query_tests).
-include_lib("eunit/include/eunit.hrl").

csv_quotes_test() ->
    ?assertEqual([<<"a">>, <<"b,c">>, <<"d\"e">>], soccer_csv:parse_line(<<"a,\"b,c\",\"d\"\"e\"">>)).

normalization_test() ->
    ?assertEqual(<<"saopaulo">>, soccer_data:normalize_team(<<"São Paulo-FC">>)),
    ?assertEqual(<<"corinthians">>, soccer_data:normalize_team(<<"Sport Club Corinthians Paulista">>)).

queries_test_() ->
    {setup, fun setup/0, fun(_) -> soccer_data:clear() end,
     fun() ->
         [?_assertEqual(2, length(soccer_query:find_matches(#{team => <<"Flamengo">>}))),
          ?_assertMatch(#{wins := 1, draws := 1, losses := 0, goals_for := 3}, soccer_query:team_stats(#{team => <<"Flamengo">>, season => 2023})),
          ?_assertMatch(#{matches := 2, team_a_wins := 1, draws := 1}, soccer_query:head_to_head(<<"Flamengo">>, <<"Fluminense">>)),
          ?_assertEqual(<<"Ana">>, maps:get(name, hd(soccer_query:find_players(#{nationality => <<"Brazil">>})))),
          ?_assertMatch([#{team := <<"Flamengo">>, points := 4}|_], soccer_query:standings(<<"Brasileirao">>, 2023))]
     end}.
setup() ->
    soccer_data:clear(), ets:new(soccer_matches,[named_table,public,set]), ets:new(soccer_players,[named_table,public,set]),
    Match1=#{home=><<"Flamengo">>,away=><<"Fluminense">>,home_key=><<"flamengo">>,away_key=><<"fluminense">>,home_goals=>2,away_goals=>1,date=><<"2023-01-02">>,season=>2023,competition=><<"Brasileirao">>,round=><<"1">>,stadium=><<>>},
    Match2=Match1#{home=><<"Fluminense">>,away=><<"Flamengo">>,home_key=><<"fluminense">>,away_key=><<"flamengo">>,home_goals=>0,away_goals=>0,date=><<"2023-02-02">>,round=><<"2">>},
    ets:insert(soccer_matches,[{1,Match1},{2,Match2}]),
    ets:insert(soccer_players,{1,#{name=><<"Ana">>,name_key=><<"ana">>,nationality=><<"Brazil">>,club=><<"Flamengo">>,position=><<"ST">>,overall=>80,potential=>85,age=>22}}), ok.
