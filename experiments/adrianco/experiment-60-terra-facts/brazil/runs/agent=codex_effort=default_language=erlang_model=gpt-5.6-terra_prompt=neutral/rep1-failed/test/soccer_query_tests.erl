-module(soccer_query_tests).
-include_lib("eunit/include/eunit.hrl").

fixture() -> #{matches => [
 #{competition=>brasileirao,home=>"Flamengo-RJ",away=>"Fluminense-RJ",home_key=>"flamengo",away_key=>"fluminense",home_goals=>2,away_goals=>1,date=>"2023-09-03",season=>2023,round=>"22"},
 #{competition=>brasileirao,home=>"Fluminense",away=>"Flamengo",home_key=>"fluminense",away_key=>"flamengo",home_goals=>1,away_goals=>1,date=>"2023-05-28",season=>2023,round=>"8"},
 #{competition=>brasileirao,home=>"Palmeiras-SP",away=>"Santos-SP",home_key=>"palmeiras",away_key=>"santos",home_goals=>4,away_goals=>0,date=>"2023-10-01",season=>2023,round=>"25"}],
 players => [#{name=>"Neymar Jr",name_key=>"neymar jr",nationality=>"Brazil",club=>"Paris Saint-Germain",club_key=>"paris saint-germain",position=>"LW",overall=>92,potential=>92}] }.

normalizes_team_names_test() -> ?assertEqual("sao paulo", soccer_data:normalize_team("São Paulo-SP")).
finds_derby_across_state_suffixes_test() -> ?assertEqual(2,length(soccer_query:matches(fixture(),#{team=>"Flamengo",opponent=>"Fluminense",season=>2023}))).
calculates_team_record_test() -> R=soccer_query:team_stats(fixture(),"Flamengo",#{season=>2023}), ?assertEqual(2,maps:get(matches,R)), ?assertEqual(1,maps:get(wins,R)), ?assertEqual(1,maps:get(draws,R)), ?assertEqual(3,maps:get(goals_for,R)).
calculates_head_to_head_test() -> R=soccer_query:head_to_head(fixture(),"Flamengo","Fluminense"), ?assertEqual(1,maps:get(team_a_wins,R)), ?assertEqual(1,maps:get(draws,R)).
filters_players_test() -> [P]=soccer_query:players(fixture(),#{nationality=>"Brazil"}), ?assertEqual("Neymar Jr",maps:get(name,P)).
calculates_standings_test() -> [Top|_]=soccer_query:standings(fixture(),brasileirao,2023), ?assertEqual("Palmeiras-SP",maps:get(team,Top)).
filters_by_date_range_test() -> ?assertEqual(1,length(soccer_query:matches(fixture(),#{date_from=>"2023-09-01",date_to=>"2023-09-30"}))).
mcp_initialization_test() -> R=soccer_mcp:handle("{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\"}",fixture()), ?assertEqual(1,maps:get(id,R)), ?assert(maps:is_key(result,R)).
