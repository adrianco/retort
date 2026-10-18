%% Feature: the provided Kaggle datasets load and answer the spec's sample questions
-module(soccer_data_tests).
-include_lib("eunit/include/eunit.hrl").

-define(DIR, "data/kaggle").

data() ->
    {ok, _} = application:ensure_all_started(kernel),
    persistent_data().

persistent_data() ->
    case persistent_term:get({?MODULE, data}, undefined) of
        undefined ->
            D = soccer_loader:load(?DIR),
            persistent_term:put({?MODULE, data}, D),
            D;
        D -> D
    end.

%% Scenario: all match files are loaded
%%   Given the six CSV files in data/kaggle
%%   When the loader runs
%%   Then matches from every competition source are present
all_sources_loaded_test_() ->
    {timeout, 60, fun() ->
        #{matches := Ms, players := Ps} = data(),
        ?assert(length(Ms) > 15000),
        ?assert(length(Ps) > 18000),
        Comps = lists:usort([maps:get(competition, M) || M <- Ms]),
        [?assert(lists:member(C, Comps)) || C <- [<<"Brasileirão Série A"/utf8>>, <<"Copa do Brasil">>,
                                                   <<"Copa Libertadores">>]]
    end}.

%% Scenario: Fla-Flu lookup
%%   Given the loaded data
%%   When I search for matches between Flamengo and Fluminense
%%   Then there are several matches, each with a date, score and competition
flu_fla_test_() ->
    {timeout, 60, fun() ->
        Ms = soccer_stats:search(maps:get(matches, data()),
                                 #{team => <<"Flamengo">>, opponent => <<"Fluminense">>}),
        ?assert(length(Ms) > 10),
        [?assert(is_map_key(competition, M) andalso is_map_key(home_goals, M)) || M <- Ms]
    end}.

%% Scenario: Copa do Brasil finals
%%   Given the loaded cup matches
%%   When I search for stage "Final" in Copa do Brasil
%%   Then each season has a final
cup_finals_test_() ->
    {timeout, 60, fun() ->
        Finals = soccer_stats:search(maps:get(matches, data()),
                                     #{competition => <<"Copa do Brasil">>, stage => <<"Final">>}),
        Seasons = lists:usort([maps:get(season, M) || M <- Finals]),
        ?assert(length(Seasons) >= 5)
    end}.

%% Scenario: Brazilian players in the FIFA data
%%   Given the loaded player data
%%   When I search for Brazilian players
%%   Then there are many, and the list is sorted by overall rating
brazilian_players_test_() ->
    {timeout, 60, fun() ->
        Ps = soccer_stats:search_players(maps:get(players, data()), #{nationality => <<"Brazil">>}),
        ?assert(length(Ps) > 500),
        Overalls = [maps:get(overall, P) || P <- Ps],
        ?assertEqual(lists:reverse(lists:sort(Overalls)), Overalls)
    end}.
