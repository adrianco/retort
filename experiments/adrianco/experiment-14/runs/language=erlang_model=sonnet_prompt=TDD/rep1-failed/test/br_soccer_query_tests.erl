-module(br_soccer_query_tests).
-include_lib("eunit/include/eunit.hrl").

-define(DATA_DIR, "data/kaggle/").

%% Setup: load all data once for the test suite
setup() ->
    br_soccer_data:load_all(?DATA_DIR).

setup_fixture() ->
    {setup, fun setup/0, fun(_) -> ok end, fun tests/1}.

tests(State) ->
    [
        ?_test(test_find_matches_by_team(State)),
        ?_test(test_find_matches_by_team_home_or_away(State)),
        ?_test(test_find_matches_by_season(State)),
        ?_test(test_find_matches_by_competition(State)),
        ?_test(test_head_to_head(State)),
        ?_test(test_team_stats(State)),
        ?_test(test_season_standings(State)),
        ?_test(test_find_players_by_name(State)),
        ?_test(test_find_players_by_nationality(State)),
        ?_test(test_find_players_by_club(State)),
        ?_test(test_top_players(State)),
        ?_test(test_biggest_wins(State)),
        ?_test(test_avg_goals(State)),
        ?_test(test_best_home_record(State))
    ].

%% Running via setup_fixture/0
br_soccer_query_test_() ->
    setup_fixture().

test_find_matches_by_team(State) ->
    Matches = br_soccer_query:find_matches_by_team(State, "Flamengo", all),
    ?assert(length(Matches) > 100),
    %% All matches should involve Flamengo
    lists:foreach(fun(M) ->
        Home = maps:get(home_team, M),
        Away = maps:get(away_team, M),
        ?assert(
            string:find(string:lowercase(Home), "flamengo") =/= nomatch orelse
            string:find(string:lowercase(Away), "flamengo") =/= nomatch
        )
    end, Matches).

test_find_matches_by_team_home_or_away(State) ->
    HomeMatches = br_soccer_query:find_matches_by_team(State, "Palmeiras", home),
    AwayMatches = br_soccer_query:find_matches_by_team(State, "Palmeiras", away),
    ?assert(length(HomeMatches) > 0),
    ?assert(length(AwayMatches) > 0),
    lists:foreach(fun(M) ->
        ?assert(string:find(string:lowercase(maps:get(home_team, M)), "palmeiras") =/= nomatch)
    end, HomeMatches),
    lists:foreach(fun(M) ->
        ?assert(string:find(string:lowercase(maps:get(away_team, M)), "palmeiras") =/= nomatch)
    end, AwayMatches).

test_find_matches_by_season(State) ->
    Matches = br_soccer_query:find_matches_by_season(State, 2019),
    ?assert(length(Matches) > 0),
    lists:foreach(fun(M) ->
        ?assertEqual(2019, maps:get(season, M))
    end, Matches).

test_find_matches_by_competition(State) ->
    Matches = br_soccer_query:find_matches_by_competition(State, "brasileirao"),
    ?assert(length(Matches) > 1000),
    CupMatches = br_soccer_query:find_matches_by_competition(State, "copa_do_brasil"),
    ?assert(length(CupMatches) > 100).

test_head_to_head(State) ->
    Result = br_soccer_query:head_to_head(State, "Flamengo", "Fluminense"),
    ?assert(maps:get(total, Result) > 10),
    ?assert(maps:is_key(team1_wins, Result)),
    ?assert(maps:is_key(team2_wins, Result)),
    ?assert(maps:is_key(draws, Result)),
    Total = maps:get(total, Result),
    W1 = maps:get(team1_wins, Result),
    W2 = maps:get(team2_wins, Result),
    D = maps:get(draws, Result),
    ?assertEqual(Total, W1 + W2 + D).

test_team_stats(State) ->
    Stats = br_soccer_query:team_stats(State, "Corinthians", "brasileirao", 2022),
    ?assert(maps:is_key(matches, Stats)),
    ?assert(maps:is_key(wins, Stats)),
    ?assert(maps:is_key(draws, Stats)),
    ?assert(maps:is_key(losses, Stats)),
    ?assert(maps:is_key(goals_for, Stats)),
    ?assert(maps:is_key(goals_against, Stats)),
    Total = maps:get(matches, Stats),
    ?assert(Total > 0),
    ?assertEqual(Total, maps:get(wins, Stats) + maps:get(draws, Stats) + maps:get(losses, Stats)).

test_season_standings(State) ->
    Standings = br_soccer_query:season_standings(State, 2019, "brasileirao"),
    ?assert(length(Standings) > 10),
    [{_Team, Points, _W, _D, _L} | _] = Standings,
    %% Flamengo won 2019 with 90 points (check they're near top)
    ?assert(Points >= 70).

test_find_players_by_name(State) ->
    Players = br_soccer_query:find_players_by_name(State, "Neymar"),
    ?assert(length(Players) > 0),
    [P | _] = Players,
    ?assert(string:find(maps:get(name, P), "Neymar") =/= nomatch).

test_find_players_by_nationality(State) ->
    Players = br_soccer_query:find_players_by_nationality(State, "Brazil"),
    %% FIFA 18/19 dataset has ~827 Brazilian players
    ?assert(length(Players) > 500),
    lists:foreach(fun(P) ->
        ?assertEqual("Brazil", maps:get(nationality, P))
    end, Players).

test_find_players_by_club(State) ->
    %% Santos and Fluminense are Brazilian clubs present in the FIFA dataset
    Players = br_soccer_query:find_players_by_club(State, "Santos"),
    ?assert(length(Players) > 0),
    lists:foreach(fun(P) ->
        Club = maps:get(club, P),
        ?assert(string:find(Club, "Santos") =/= nomatch)
    end, Players).

test_top_players(State) ->
    Players = br_soccer_query:top_players(State, #{nationality => "Brazil", limit => 5}),
    ?assertEqual(5, length(Players)),
    Ratings = [maps:get(overall, P) || P <- Players],
    %% Should be sorted descending
    ?assertEqual(Ratings, lists:sort(fun(A, B) -> A >= B end, Ratings)).

test_biggest_wins(State) ->
    Wins = br_soccer_query:biggest_wins(State, 5),
    ?assertEqual(5, length(Wins)),
    [{M1, Diff1} | Rest] = Wins,
    ?assert(Diff1 >= 4),
    ?assert(maps:is_key(home_team, M1)),
    Diffs = [D || {_, D} <- Wins],
    ?assertEqual(Diffs, lists:sort(fun(A, B) -> A >= B end, Diffs)).

test_avg_goals(State) ->
    Avg = br_soccer_query:avg_goals_per_match(State, "brasileirao"),
    ?assert(Avg > 1.5),
    ?assert(Avg < 5.0).

test_best_home_record(State) ->
    Records = br_soccer_query:best_home_records(State, "brasileirao", 5),
    ?assertEqual(5, length(Records)),
    [{_Team, WinRate} | _] = Records,
    ?assert(WinRate > 0.3),
    ?assert(WinRate =< 1.0).
