%%%-------------------------------------------------------------------
%%% @doc Feature: Statistical Analysis.
%%%
%%% Context: the aggregate side of the specification - goals per match,
%%% home advantage, season comparisons and biggest wins.  The assertions
%%% are deliberately expressed as invariants (percentages sum to 100,
%%% goals for equal goals against league wide, margins are ordered)
%%% rather than as frozen numbers, so they keep their meaning if the
%%% data directory is refreshed.
%%% @end
%%%-------------------------------------------------------------------
-module(statistics_SUITE).

-compile([export_all, nowarn_export_all]).

-include_lib("common_test/include/ct.hrl").
-include_lib("stdlib/include/assert.hrl").

-import(bsmcp_bdd, [feature/1, scenario/1, given/2, when_/2, then/2, and_/2,
                    call_tool/2, call_tool_error/2]).

all() ->
    [average_goals_per_match,
     home_advantage_is_measured,
     compare_two_seasons,
     biggest_wins_in_the_dataset,
     biggest_wins_for_one_club,
     statistics_respect_filters].

init_per_suite(Config) ->
    bsmcp_test_helper:start(),
    Config.

end_per_suite(_Config) ->
    ok.

init_per_testcase(_Case, Config) ->
    feature("Statistical Analysis"),
    Config.

%%--------------------------------------------------------------------

average_goals_per_match(_Config) ->
    scenario("What's the average goals per match in the Brasileirao?"),
    {Result, Text} = when_("I ask for Serie A competition statistics", fun() ->
        call_tool(<<"competition_stats">>, #{<<"competition">> => <<"serie a">>})
    end),
    Overall = maps:get(overall, Result),
    then("the average is a plausible football number", fun() ->
        G = maps:get(goals_per_match, Overall),
        G > 2.0 andalso G < 3.5
    end),
    and_("it equals total goals divided by matches", fun() ->
        Expected = bsmcp_text:round2(maps:get(goals, Overall) / maps:get(matches, Overall)),
        Expected =:= maps:get(goals_per_match, Overall)
    end),
    and_("home, away and draw percentages add up to 100", fun() ->
        Sum = maps:get(home_win_pct, Overall) + maps:get(away_win_pct, Overall)
            + maps:get(draw_pct, Overall),
        abs(Sum - 100.0) < 0.2
    end),
    and_("the text answer states the average", fun() ->
        binary:match(Text, <<"per match">>) =/= nomatch
    end).

home_advantage_is_measured(_Config) ->
    scenario("Home advantage shows up across the whole dataset"),
    {Result, _} = when_("I ask for statistics over every competition", fun() ->
        call_tool(<<"competition_stats">>, #{})
    end),
    Overall = maps:get(overall, Result),
    then("home wins outnumber away wins", fun() ->
        maps:get(home_wins, Overall) > maps:get(away_wins, Overall)
    end),
    and_("home goals outnumber away goals", fun() ->
        maps:get(home_goals, Overall) > maps:get(away_goals, Overall)
    end),
    and_("home and away goals sum to the total", fun() ->
        maps:get(home_goals, Overall) + maps:get(away_goals, Overall)
            =:= maps:get(goals, Overall)
    end).

compare_two_seasons(_Config) ->
    scenario("Compare the 2018 and 2019 seasons"),
    {Result, Text} = when_("I ask for Serie A statistics for both seasons", fun() ->
        call_tool(<<"competition_stats">>, #{<<"competition">> => <<"serie a">>,
                                             <<"seasons">> => [2018, 2019]})
    end),
    BySeason = maps:get(by_season, Result),
    then("both seasons are reported separately", fun() ->
        [maps:get(season, S) || S <- BySeason] =:= [2018, 2019]
    end),
    and_("each season has a full 380 match programme", fun() ->
        lists:all(fun(S) -> maps:get(matches, maps:get(stats, S)) =:= 380 end, BySeason)
    end),
    and_("the seasons sum to the combined total", fun() ->
        lists:sum([maps:get(matches, maps:get(stats, S)) || S <- BySeason])
            =:= maps:get(matches, maps:get(overall, Result))
    end),
    and_("the text answer breaks the seasons out", fun() ->
        binary:match(Text, <<"By season">>) =/= nomatch
    end).

biggest_wins_in_the_dataset(_Config) ->
    scenario("Show me the biggest wins in the dataset"),
    {Result, Text} = when_("I ask for the biggest winning margins", fun() ->
        call_tool(<<"biggest_wins">>, #{<<"limit">> => 10})
    end),
    Matches = maps:get(matches, Result),
    then("ten matches come back ordered by margin", fun() ->
        Margins = [maps:get(margin, M) || M <- Matches],
        length(Margins) =:= 10 andalso Margins =:= lists:reverse(lists:sort(Margins))
    end),
    and_("the biggest margin is at least seven goals", fun() ->
        maps:get(margin, hd(Matches)) >= 7
    end),
    and_("every listed match really was a win", fun() ->
        lists:all(fun(#{result := R}) -> R =/= draw andalso R =/= undefined end, Matches)
    end),
    and_("each line shows the date, teams and score", fun() ->
        binary:match(Text, <<"-">>) =/= nomatch
    end).

biggest_wins_for_one_club(_Config) ->
    scenario("Biggest wins can be scoped to one club and competition"),
    {Result, _} = when_("I ask for Santos' biggest Serie A wins", fun() ->
        call_tool(<<"biggest_wins">>, #{<<"team">> => <<"Santos">>,
                                        <<"competition">> => <<"serie a">>,
                                        <<"limit">> => 5})
    end),
    then("every match involves Santos in Serie A", fun() ->
        lists:all(fun(M) ->
                          maps:get(competition, M) =:= serie_a andalso
                              lists:member(<<"Santos-SP">>,
                                           [maps:get(home_team, M), maps:get(away_team, M)])
                  end, maps:get(matches, Result))
    end),
    and_("and every one of them is a Santos win, not a heavy defeat", fun() ->
        lists:all(fun(M) ->
                          case maps:get(result, M) of
                              home -> maps:get(home_team, M) =:= <<"Santos-SP">>;
                              away -> maps:get(away_team, M) =:= <<"Santos-SP">>
                          end
                  end, maps:get(matches, Result))
    end).

statistics_respect_filters(_Config) ->
    scenario("Filtered statistics are a strict subset of unfiltered ones"),
    {All, _} = when_("I ask for all Serie A statistics", fun() ->
        call_tool(<<"competition_stats">>, #{<<"competition">> => <<"serie a">>})
    end),
    {One, _} = and_("I ask for the 2019 season only", fun() ->
        call_tool(<<"competition_stats">>, #{<<"competition">> => <<"serie a">>,
                                             <<"season">> => 2019})
    end),
    then("the filtered set is smaller", fun() ->
        maps:get(matches, maps:get(overall, One)) =:= 380
            andalso maps:get(matches, maps:get(overall, One))
                    < maps:get(matches, maps:get(overall, All))
    end),
    {Team, _} = and_("I ask for one club inside that season", fun() ->
        call_tool(<<"competition_stats">>, #{<<"competition">> => <<"serie a">>,
                                             <<"season">> => 2019,
                                             <<"team">> => <<"Flamengo">>})
    end),
    then("only that club's 38 matches are counted", fun() ->
        maps:get(matches, maps:get(overall, Team)) =:= 38
    end).
