%%%-------------------------------------------------------------------
%%% @doc Feature: Team Queries.
%%%
%%% Context: the specification's second capability - club records,
%%% home/away splits, head-to-head comparisons and "which club is best
%%% at X" rankings.  The expected numbers below were cross-checked
%%% against the published Brasileirão tables, so these scenarios double
%%% as a correctness check on the de-duplication of the overlapping
%%% source files.
%%% @end
%%%-------------------------------------------------------------------
-module(team_queries_SUITE).

-compile([export_all, nowarn_export_all]).

-include_lib("common_test/include/ct.hrl").
-include_lib("stdlib/include/assert.hrl").

-import(bsmcp_bdd, [feature/1, scenario/1, given/2, when_/2, then/2, and_/2,
                    call_tool/2, call_tool_error/2]).

all() ->
    [home_record_for_a_season,
     full_season_record_matches_published_table,
     head_to_head_between_two_clubs,
     head_to_head_is_internally_consistent,
     team_profile_lists_competitions,
     highest_scoring_team_of_a_season,
     best_home_record_overall,
     record_splits_add_up].

init_per_suite(Config) ->
    bsmcp_test_helper:start(),
    Config.

end_per_suite(_Config) ->
    ok.

init_per_testcase(_Case, Config) ->
    feature("Team Queries"),
    Config.

%%--------------------------------------------------------------------

home_record_for_a_season(_Config) ->
    scenario("What is Corinthians' home record in 2022?"),
    {Result, Text} = when_("I request Corinthians home statistics for 2022", fun() ->
        call_tool(<<"team_stats">>, #{<<"team">> => <<"Corinthians">>,
                                      <<"season">> => 2022,
                                      <<"competition">> => <<"serie a">>,
                                      <<"venue">> => <<"home">>})
    end),
    Record = maps:get(record, Result),
    then("I should receive wins, losses, draws and goals", fun() ->
        lists:all(fun(K) -> is_integer(maps:get(K, Record)) end,
                  [played, wins, draws, losses, goals_for, goals_against, points])
    end),
    and_("the 19 home fixtures of a 38 round season are counted", fun() ->
        maps:get(played, Record) =:= 19
    end),
    and_("wins, draws and losses add up to the matches played", fun() ->
        maps:get(wins, Record) + maps:get(draws, Record) + maps:get(losses, Record)
            =:= maps:get(played, Record)
    end),
    and_("the answer is rendered for a human", fun() ->
        binary:match(Text, <<"Win rate">>) =/= nomatch
    end).

full_season_record_matches_published_table(_Config) ->
    scenario("A club's season record matches the published table"),
    {Result, _} = when_("I request Flamengo statistics for the 2019 Serie A", fun() ->
        call_tool(<<"team_stats">>, #{<<"team">> => <<"Flamengo">>,
                                      <<"season">> => 2019,
                                      <<"competition">> => <<"serie a">>})
    end),
    R = maps:get(record, Result),
    then("Flamengo played 38 matches", fun() -> maps:get(played, R) =:= 38 end),
    and_("the record is 28 wins, 6 draws, 4 losses", fun() ->
        {maps:get(wins, R), maps:get(draws, R), maps:get(losses, R)} =:= {28, 6, 4}
    end),
    and_("they collected 90 points with 86 goals scored", fun() ->
        {maps:get(points, R), maps:get(goals_for, R)} =:= {90, 86}
    end).

head_to_head_between_two_clubs(_Config) ->
    scenario("Compare Palmeiras and Santos head-to-head"),
    {Result, Text} = when_("I ask for the head-to-head record", fun() ->
        call_tool(<<"head_to_head">>, #{<<"team_a">> => <<"Palmeiras">>,
                                        <<"team_b">> => <<"Santos">>,
                                        <<"limit">> => 5})
    end),
    Summary = maps:get(summary, Result),
    then("both clubs are resolved", fun() ->
        maps:get(name, maps:get(team_a, Result)) =:= <<"Palmeiras">>
            andalso maps:get(name, maps:get(team_b, Result)) =:= <<"Santos-SP">>
    end),
    and_("wins, draws and goals are reported for both", fun() ->
        maps:get(played, Summary) > 20
            andalso maps:get(team_a_goals, Summary) > 0
            andalso maps:get(team_b_goals, Summary) > 0
    end),
    and_("a per competition breakdown is included", fun() ->
        length(maps:get(by_competition, Result)) >= 1
    end),
    and_("the text answer names both clubs", fun() ->
        binary:match(Text, <<"Palmeiras">>) =/= nomatch
            andalso binary:match(Text, <<"Santos">>) =/= nomatch
    end).

head_to_head_is_internally_consistent(_Config) ->
    scenario("Head-to-head totals are consistent"),
    {Result, _} = when_("I ask for Gremio versus Internacional", fun() ->
        call_tool(<<"head_to_head">>, #{<<"team_a">> => <<"Gremio">>,
                                        <<"team_b">> => <<"Internacional">>})
    end),
    S = maps:get(summary, Result),
    then("wins plus draws equal the matches played", fun() ->
        maps:get(team_a_wins, S) + maps:get(team_b_wins, S) + maps:get(draws, S)
            =:= maps:get(played, S)
    end),
    and_("the per competition matches sum to the total", fun() ->
        lists:sum([maps:get(matches, C) || C <- maps:get(by_competition, Result)])
            =:= maps:get(played, S)
    end).

team_profile_lists_competitions(_Config) ->
    scenario("What competitions has Palmeiras played in?"),
    {Result, Text} = when_("I request the Palmeiras profile", fun() ->
        call_tool(<<"team_profile">>, #{<<"team">> => <<"Palmeiras">>})
    end),
    Comps = [maps:get(competition, C) || C <- maps:get(competitions, Result)],
    then("the three competitions it appears in are listed", fun() ->
        lists:member(serie_a, Comps) andalso lists:member(copa_do_brasil, Comps)
            andalso lists:member(libertadores, Comps)
    end),
    and_("first match, last match and biggest win are reported", fun() ->
        maps:get(first_match, Result) =/= undefined
            andalso maps:get(last_match, Result) =/= undefined
            andalso maps:get(biggest_win, Result) =/= undefined
    end),
    and_("the biggest win really is a win", fun() ->
        #{home_team := H, result := Res} = maps:get(biggest_win, Result),
        (H =:= <<"Palmeiras">> andalso Res =:= home)
            orelse (H =/= <<"Palmeiras">> andalso Res =:= away)
    end),
    and_("the text answer mentions the competitions", fun() ->
        binary:match(Text, <<"Copa Libertadores">>) =/= nomatch
    end).

highest_scoring_team_of_a_season(_Config) ->
    scenario("Which team scored the most goals in Serie A 2023?"),
    {Result, _} = when_("I rank clubs by goals scored", fun() ->
        call_tool(<<"league_leaderboard">>, #{<<"metric">> => <<"goals_for">>,
                                             <<"competition">> => <<"serie a">>,
                                             <<"season">> => 2023,
                                             <<"limit">> => 5})
    end),
    Rows = maps:get(leaderboard, Result),
    then("the ranking is ordered by the metric", fun() ->
        Values = [maps:get(value, R) || R <- Rows],
        Values =:= lists:reverse(lists:sort(Values))
    end),
    and_("the leader scored more than 50 goals", fun() ->
        maps:get(value, hd(Rows)) > 50
    end).

best_home_record_overall(_Config) ->
    scenario("Which team has the best home record?"),
    {Result, _} = when_("I rank clubs by home win rate with a minimum of 100 matches",
                        fun() ->
                            call_tool(<<"league_leaderboard">>,
                                      #{<<"metric">> => <<"home_win_rate">>,
                                        <<"competition">> => <<"serie a">>,
                                        <<"min_played">> => 100,
                                        <<"limit">> => 5})
                        end),
    Rows = maps:get(leaderboard, Result),
    then("only clubs above the threshold are ranked", fun() ->
        lists:all(fun(R) -> maps:get(played, R) >= 100 end, Rows)
    end),
    and_("the best home win rate is above 50 percent", fun() ->
        maps:get(value, hd(Rows)) > 50.0
    end).

record_splits_add_up(_Config) ->
    scenario("Home and away splits add up to the overall record"),
    {Result, _} = when_("I request the overall Cruzeiro record", fun() ->
        call_tool(<<"team_stats">>, #{<<"team">> => <<"Cruzeiro">>})
    end),
    R = maps:get(record, Result),
    Home = maps:get(home, R),
    Away = maps:get(away, R),
    then("played splits add up", fun() ->
        maps:get(played, Home) + maps:get(played, Away) =:= maps:get(played, R)
    end),
    and_("goals splits add up", fun() ->
        maps:get(goals_for, Home) + maps:get(goals_for, Away) =:= maps:get(goals_for, R)
    end),
    and_("points equal three per win plus one per draw", fun() ->
        maps:get(points, R) =:= maps:get(wins, R) * 3 + maps:get(draws, R)
    end).
