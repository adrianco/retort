-module(br_soccer_data_tests).
-include_lib("eunit/include/eunit.hrl").

-define(DATA_DIR, "data/kaggle/").

load_brasileirao_test() ->
    Matches = br_soccer_data:load_brasileirao(?DATA_DIR),
    ?assert(length(Matches) > 4000),
    [First | _] = Matches,
    ?assert(maps:is_key(home_team, First)),
    ?assert(maps:is_key(away_team, First)),
    ?assert(maps:is_key(home_goal, First)),
    ?assert(maps:is_key(away_goal, First)),
    ?assert(maps:is_key(season, First)),
    ?assert(maps:is_key(date, First)).

load_cup_test() ->
    Matches = br_soccer_data:load_cup(?DATA_DIR),
    ?assert(length(Matches) > 1000),
    [First | _] = Matches,
    ?assert(maps:is_key(home_team, First)),
    ?assert(maps:is_key(away_team, First)).

load_libertadores_test() ->
    Matches = br_soccer_data:load_libertadores(?DATA_DIR),
    ?assert(length(Matches) > 1200),
    [First | _] = Matches,
    ?assert(maps:is_key(stage, First)).

load_br_football_test() ->
    Matches = br_soccer_data:load_br_football(?DATA_DIR),
    ?assert(length(Matches) > 10000),
    [First | _] = Matches,
    ?assert(maps:is_key(tournament, First)),
    ?assert(maps:is_key(home_corner, First)).

load_historico_test() ->
    Matches = br_soccer_data:load_historico(?DATA_DIR),
    ?assert(length(Matches) > 6000),
    [First | _] = Matches,
    ?assert(maps:is_key(arena, First)),
    ?assert(maps:is_key(winner, First)).

load_players_test() ->
    Players = br_soccer_data:load_players(?DATA_DIR),
    ?assert(length(Players) > 18000),
    [First | _] = Players,
    ?assert(maps:is_key(name, First)),
    ?assert(maps:is_key(nationality, First)),
    ?assert(maps:is_key(overall, First)),
    ?assert(maps:is_key(club, First)).

team_name_normalized_test() ->
    Matches = br_soccer_data:load_brasileirao(?DATA_DIR),
    [First | _] = Matches,
    HomeTeam = maps:get(home_team, First),
    %% Should not contain state suffix
    ?assertEqual(nomatch, re:run(HomeTeam, "-[A-Z]{2}$")).

season_is_integer_test() ->
    Matches = br_soccer_data:load_brasileirao(?DATA_DIR),
    [First | _] = Matches,
    ?assert(is_integer(maps:get(season, First))).

player_overall_is_integer_test() ->
    Players = br_soccer_data:load_players(?DATA_DIR),
    [First | _] = Players,
    ?assert(is_integer(maps:get(overall, First))).
