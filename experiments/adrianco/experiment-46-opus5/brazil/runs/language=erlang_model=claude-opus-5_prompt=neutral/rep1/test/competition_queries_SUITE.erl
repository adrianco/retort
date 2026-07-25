%%%-------------------------------------------------------------------
%%% @doc Feature: Competition Queries.
%%%
%%% Context: league tables are *calculated* from the merged match
%%% records, which makes them the sharpest available test of the whole
%%% ingest pipeline: if de-duplication across the three overlapping
%%% Série A sources were wrong, the 2019 champion would not have exactly
%%% 90 points from 38 matches.  Seasons whose fixtures are incomplete in
%%% the data must refuse to crown anybody.
%%% @end
%%%-------------------------------------------------------------------
-module(competition_queries_SUITE).

-compile([export_all, nowarn_export_all]).

-include_lib("common_test/include/ct.hrl").
-include_lib("stdlib/include/assert.hrl").

-import(bsmcp_bdd, [feature/1, scenario/1, given/2, when_/2, then/2, and_/2,
                    call_tool/2, call_tool_error/2]).

all() ->
    [who_won_the_2019_brasileirao,
     relegation_zone_of_a_season,
     table_arithmetic_is_sound,
     incomplete_season_is_not_crowned,
     standings_requires_a_season,
     unknown_competition_lists_the_valid_ones,
     historical_seasons_are_available,
     cup_and_continental_competitions_have_no_champion_row].

init_per_suite(Config) ->
    bsmcp_test_helper:start(),
    Config.

end_per_suite(_Config) ->
    ok.

init_per_testcase(_Case, Config) ->
    feature("Competition Queries"),
    Config.

%%--------------------------------------------------------------------

who_won_the_2019_brasileirao(_Config) ->
    scenario("Who won the 2019 Brasileirao?"),
    {Result, Text} = when_("I request the 2019 Serie A standings", fun() ->
        call_tool(<<"standings">>, #{<<"competition">> => <<"brasileirao">>,
                                     <<"season">> => 2019})
    end),
    then("the table is built from all 380 fixtures", fun() ->
        maps:get(matches, Result) =:= 380 andalso maps:get(teams, Result) =:= 20
    end),
    and_("the season is recognised as complete", fun() ->
        maps:get(complete, Result) =:= true
    end),
    and_("Flamengo is champion with 90 points", fun() ->
        [Top | _] = maps:get(table, Result),
        maps:get(champion, Result) =:= <<"Flamengo-RJ">>
            andalso maps:get(points, Top) =:= 90
            andalso maps:get(wins, Top) =:= 28
    end),
    and_("the runners up match the published table", fun() ->
        [_, Second, Third | _] = maps:get(table, Result),
        {maps:get(team_name, Second), maps:get(points, Second)} =:= {<<"Santos-SP">>, 74}
            andalso {maps:get(team_name, Third), maps:get(points, Third)}
                    =:= {<<"Palmeiras">>, 74}
    end),
    and_("the text answer marks the champion", fun() ->
        binary:match(Text, <<"Champion">>) =/= nomatch
    end).

relegation_zone_of_a_season(_Config) ->
    scenario("Which teams were relegated in 2019?"),
    {Result, _} = when_("I request the 2019 standings", fun() ->
        call_tool(<<"standings">>, #{<<"competition">> => <<"serie a">>,
                                     <<"season">> => 2019})
    end),
    then("four clubs are in the relegation zone", fun() ->
        length(maps:get(relegated, Result)) =:= 4
    end),
    and_("they are the four published relegations", fun() ->
        lists:sort(maps:get(relegated, Result))
            =:= lists:sort([<<"Cruzeiro">>, <<"CSA">>, <<"Chapecoense">>,
                            <<"Avaí"/utf8>>])
    end),
    and_("they occupy the last four positions", fun() ->
        Table = maps:get(table, Result),
        Bottom = lists:nthtail(length(Table) - 4, Table),
        lists:sort([maps:get(team_name, R) || R <- Bottom])
            =:= lists:sort(maps:get(relegated, Result))
    end).

table_arithmetic_is_sound(_Config) ->
    scenario("Every row of a table is arithmetically consistent"),
    {Result, _} = when_("I request the 2018 standings", fun() ->
        call_tool(<<"standings">>, #{<<"competition">> => <<"serie a">>,
                                     <<"season">> => 2018})
    end),
    Table = maps:get(table, Result),
    then("each row's results add up to its matches played", fun() ->
        lists:all(fun(R) ->
                          maps:get(wins, R) + maps:get(draws, R) + maps:get(losses, R)
                              =:= maps:get(played, R)
                  end, Table)
    end),
    and_("each row's points follow the three point rule", fun() ->
        lists:all(fun(R) ->
                          maps:get(points, R) =:= maps:get(wins, R) * 3 + maps:get(draws, R)
                  end, Table)
    end),
    and_("goals scored across the league equal goals conceded", fun() ->
        lists:sum([maps:get(goals_for, R) || R <- Table])
            =:= lists:sum([maps:get(goals_against, R) || R <- Table])
    end),
    and_("the table is sorted by points", fun() ->
        Points = [maps:get(points, R) || R <- Table],
        Points =:= lists:reverse(lists:sort(Points))
    end).

incomplete_season_is_not_crowned(_Config) ->
    scenario("A season with missing fixtures gets no champion"),
    {Result, Text} = when_("I request the 2023 standings", fun() ->
        call_tool(<<"standings">>, #{<<"competition">> => <<"serie a">>,
                                     <<"season">> => 2023})
    end),
    then("the season is flagged as incomplete", fun() ->
        maps:get(complete, Result) =:= false
    end),
    and_("no champion and no relegation zone are claimed", fun() ->
        maps:get(champion, Result) =:= undefined
            andalso maps:get(relegated, Result) =:= undefined
    end),
    and_("the text answer says so", fun() ->
        binary:match(Text, <<"missing some fixtures">>) =/= nomatch
    end),
    and_("the partial table is still returned", fun() ->
        length(maps:get(table, Result)) =:= 20
    end).

standings_requires_a_season(_Config) ->
    scenario("Asking for a table without a season is guided, not failed"),
    {Error, Text} = when_("I request standings with no season", fun() ->
        call_tool_error(<<"standings">>, #{<<"competition">> => <<"serie a">>})
    end),
    then("the tool asks for a season", fun() ->
        maps:get(error, Error) =:= missing_season
    end),
    and_("it lists the seasons that are available", fun() ->
        length(maps:get(available_seasons, Error)) >= 20
            andalso binary:match(Text, <<"2019">>) =/= nomatch
    end).

unknown_competition_lists_the_valid_ones(_Config) ->
    scenario("An unknown competition name lists the valid ones"),
    {Error, _} = when_("I ask for the \"Premier League\" table", fun() ->
        call_tool_error(<<"standings">>, #{<<"competition">> => <<"Premier League">>,
                                           <<"season">> => 2019})
    end),
    then("the tool reports an unknown competition", fun() ->
        maps:get(error, Error) =:= unknown_competition
    end),
    and_("all five loaded competitions are offered", fun() ->
        length(maps:get(available, Error)) =:= 5
    end).

historical_seasons_are_available(_Config) ->
    scenario("The historical file extends coverage back to 2003"),
    {Result, _} = when_("I request the 2003 standings", fun() ->
        call_tool(<<"standings">>, #{<<"competition">> => <<"serie a">>,
                                     <<"season">> => 2003})
    end),
    then("the 24 team format of that season is reflected", fun() ->
        maps:get(teams, Result) =:= 24 andalso maps:get(matches, Result) =:= 552
    end),
    and_("Cruzeiro is champion with 100 points", fun() ->
        [Top | _] = maps:get(table, Result),
        maps:get(team_name, Top) =:= <<"Cruzeiro">> andalso maps:get(points, Top) =:= 100
    end).

cup_and_continental_competitions_have_no_champion_row(_Config) ->
    scenario("Knockout competitions are summarised without crowning a league champion"),
    {Result, _} = when_("I request a Libertadores season summary", fun() ->
        call_tool(<<"standings">>, #{<<"competition">> => <<"libertadores">>,
                                     <<"season">> => 2019})
    end),
    then("matches are aggregated", fun() ->
        maps:get(matches, Result) > 100
    end),
    and_("no champion is inferred from a knockout format", fun() ->
        maps:get(champion, Result) =:= undefined
            andalso maps:get(relegated, Result) =:= undefined
    end).
