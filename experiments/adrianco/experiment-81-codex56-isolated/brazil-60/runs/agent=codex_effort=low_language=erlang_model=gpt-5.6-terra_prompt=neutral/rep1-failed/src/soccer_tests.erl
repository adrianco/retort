-module(soccer_tests).
-compile({encoding, utf8}).
-include_lib("eunit/include/eunit.hrl").
sample() -> #{matches=>[#{date=><<"2023-01-01">>,date_sort=>20230101,season=>2023,competition=><<"Brasileirao">>,home=><<"Palmeiras-SP">>,away=><<"Santos">>,home_normalized=><<"palmeiras">>,away_normalized=><<"santos">>,home_goals=>2,away_goals=>1,round=><<"1">>,stage=><<>>},#{date=><<"2023-02-01">>,date_sort=>20230201,season=>2023,competition=><<"Brasileirao">>,home=><<"Santos">>,away=><<"Palmeiras">>,home_normalized=><<"santos">>,away_normalized=><<"palmeiras">>,home_goals=>1,away_goals=>1,round=><<"2">>,stage=><<>>}],players=>[#{name=><<"Joao">>,nationality=><<"Brazil">>,club=><<"Flamengo">>,position=><<"ST">>,overall=>80,age=>25,potential=>81,id=><<"1">>,jersey_number=>9}]}.
normalization_test()->?assertEqual(<<"sao paulo">>,soccer_data:normalize_team(<<"S",195,163,"o Paulo-SP">>)).
match_query_test()->?assertEqual(2,length(soccer_query:find_matches(sample(),#{team=><<"Palmeiras">>}))).
stats_test()->S=soccer_query:team_stats(sample(),#{team=><<"Palmeiras">>,season=>2023}),?assertEqual(1,maps:get(wins,S)),?assertEqual(1,maps:get(draws,S)).
standings_test()->[First|_]=soccer_query:standings(sample(),<<"Brasileirao">>,2023),?assertEqual(<<"Palmeiras-SP">>,maps:get(team,First)).
json_test()->?assertEqual({ok,#{<<"x">>=>[1,true]}},soccer_json:decode(<<"{\"x\":[1,true]}">>)).
