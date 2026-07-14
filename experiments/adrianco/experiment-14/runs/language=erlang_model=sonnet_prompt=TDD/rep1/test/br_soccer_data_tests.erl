-module(br_soccer_data_tests).
-include_lib("eunit/include/eunit.hrl").

%% These tests load actual CSV files.
data_dir() ->
    filename:join([filename:absname("data"), "kaggle"]).

%% TDD Cycle 1: Load Brasileirao matches
load_brasileirao_test() ->
    Rows = br_soccer_data:load_brasileirao(data_dir()),
    ?assert(length(Rows) > 4000),
    First = hd(Rows),
    ?assert(maps:is_key(<<"home_team">>, First)),
    ?assert(maps:is_key(<<"season">>, First)).

%% TDD Cycle 2: Load Copa do Brasil
load_copa_test() ->
    Rows = br_soccer_data:load_copa_brasil(data_dir()),
    ?assert(length(Rows) > 1000),
    First = hd(Rows),
    ?assert(maps:is_key(<<"home_team">>, First)).

%% TDD Cycle 3: Load Libertadores
load_libertadores_test() ->
    Rows = br_soccer_data:load_libertadores(data_dir()),
    ?assert(length(Rows) > 1200),
    First = hd(Rows),
    ?assert(maps:is_key(<<"stage">>, First)).

%% TDD Cycle 4: Load extended BR Football Dataset
load_br_football_test() ->
    Rows = br_soccer_data:load_br_football(data_dir()),
    ?assert(length(Rows) > 10000),
    First = hd(Rows),
    ?assert(maps:is_key(<<"tournament">>, First)).

%% TDD Cycle 5: Load historical Brasileirao
load_historical_test() ->
    Rows = br_soccer_data:load_historical(data_dir()),
    ?assert(length(Rows) > 6000),
    First = hd(Rows),
    ?assert(maps:is_key(<<"Equipe_mandante">>, First)).

%% TDD Cycle 6: Load FIFA players
load_players_test() ->
    Rows = br_soccer_data:load_players(data_dir()),
    ?assert(length(Rows) > 18000),
    First = hd(Rows),
    ?assert(maps:is_key(<<"Name">>, First)),
    ?assert(maps:is_key(<<"Overall">>, First)).

%% TDD Cycle 7: load_all returns a map of all datasets
load_all_test() ->
    All = br_soccer_data:load_all(data_dir()),
    ?assert(maps:is_key(brasileirao, All)),
    ?assert(maps:is_key(copa_brasil, All)),
    ?assert(maps:is_key(libertadores, All)),
    ?assert(maps:is_key(br_football, All)),
    ?assert(maps:is_key(historical, All)),
    ?assert(maps:is_key(players, All)).

%% TDD Cycle 8: all_matches returns unified list with competition field
all_matches_test() ->
    All = br_soccer_data:load_all(data_dir()),
    Matches = br_soccer_data:all_matches(All),
    ?assert(length(Matches) > 20000),
    First = hd(Matches),
    ?assert(maps:is_key(competition, First)).
