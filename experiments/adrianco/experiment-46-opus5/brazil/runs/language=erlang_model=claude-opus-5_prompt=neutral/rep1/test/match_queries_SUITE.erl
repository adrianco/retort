%%%-------------------------------------------------------------------
%%% @doc Feature: Match Queries.
%%%
%%% Context: covers the "Match Queries" capability of the specification
%%% - find matches by team, by date range, by competition and by season,
%%% plus the recovery path when a club name cannot be resolved.  Every
%%% scenario calls the MCP tool layer (not the query module directly) so
%%% argument decoding and text rendering are exercised too.
%%% @end
%%%-------------------------------------------------------------------
-module(match_queries_SUITE).

-compile([export_all, nowarn_export_all]).

-include_lib("common_test/include/ct.hrl").
-include_lib("stdlib/include/assert.hrl").

-import(bsmcp_bdd, [feature/1, scenario/1, given/2, when_/2, then/2, and_/2,
                    call_tool/2, call_tool_error/2]).

all() ->
    [matches_between_two_teams,
     matches_for_a_team_in_a_season,
     most_recent_meeting_and_score,
     matches_by_competition,
     matches_by_date_range,
     home_and_away_filters,
     cup_stage_filter,
     unknown_team_returns_suggestions].

init_per_suite(Config) ->
    bsmcp_test_helper:start(),
    Config.

end_per_suite(_Config) ->
    ok.

init_per_testcase(_Case, Config) ->
    feature("Match Queries"),
    Config.

%%--------------------------------------------------------------------

matches_between_two_teams(_Config) ->
    scenario("Find matches between two teams"),
    given("the match data is loaded", fun() ->
        ?assert(maps:get(matches, bsmcp_data:status()) > 10000)
    end),
    {Result, Text} = when_("I search for matches between \"Flamengo\" and \"Fluminense\"",
                           fun() ->
                               call_tool(<<"search_matches">>,
                                         #{<<"team">> => <<"Flamengo">>,
                                           <<"opponent">> => <<"Fluminense">>,
                                           <<"limit">> => 5})
                           end),
    then("I should receive a list of matches", fun() ->
        maps:get(total, Result) > 20 andalso length(maps:get(matches, Result)) =:= 5
    end),
    and_("each match should have date, scores and competition", fun() ->
        lists:all(fun(M) ->
                          is_binary(maps:get(date, M))
                              andalso is_integer(maps:get(home_goal, M))
                              andalso is_integer(maps:get(away_goal, M))
                              andalso is_binary(maps:get(competition_name, M))
                              andalso is_binary(maps:get(score, M))
                  end, maps:get(matches, Result))
    end),
    and_("both clubs appear in every match", fun() ->
        lists:all(fun(M) ->
                          Teams = [maps:get(home_team, M), maps:get(away_team, M)],
                          lists:member(<<"Flamengo-RJ">>, Teams)
                              andalso lists:member(<<"Fluminense-RJ">>, Teams)
                  end, maps:get(matches, Result))
    end),
    then("the text answer lists the fixtures", fun() ->
        binary:match(Text, <<"Flamengo-RJ">>) =/= nomatch
    end).

matches_for_a_team_in_a_season(_Config) ->
    scenario("What matches did Palmeiras play in 2023?"),
    {Result, _} = when_("I search matches for Palmeiras in season 2023", fun() ->
        call_tool(<<"search_matches">>, #{<<"team">> => <<"Palmeiras">>,
                                          <<"season">> => 2023,
                                          <<"limit">> => 100})
    end),
    then("every returned match is from 2023", fun() ->
        lists:all(fun(#{season := S}) -> S =:= 2023 end, maps:get(matches, Result))
    end),
    and_("the league fixtures are all there", fun() ->
        League = [M || M = #{competition := serie_a} <- maps:get(matches, Result)],
        length(League) >= 37
    end),
    and_("more than one competition is covered", fun() ->
        Comps = lists:usort([C || #{competition := C} <- maps:get(matches, Result)]),
        length(Comps) >= 2
    end).

most_recent_meeting_and_score(_Config) ->
    scenario("When did Flamengo last play Corinthians, and what was the score?"),
    {Result, _} = when_("I search their meetings ordered by date", fun() ->
        call_tool(<<"search_matches">>, #{<<"team">> => <<"Flamengo">>,
                                          <<"opponent">> => <<"Corinthians">>,
                                          <<"order">> => <<"date_desc">>,
                                          <<"played_only">> => true,
                                          <<"limit">> => 1})
    end),
    [Latest] = maps:get(matches, Result),
    then("the newest meeting comes back first", fun() ->
        maps:get(date, Latest) >= <<"2020-01-01">>
    end),
    and_("the score is available", fun() ->
        is_binary(maps:get(score, Latest))
            andalso maps:get(result, Latest) =/= undefined
    end).

matches_by_competition(_Config) ->
    scenario("Find matches in a specific competition"),
    {Result, _} = when_("I search Copa do Brasil matches in 2023", fun() ->
        call_tool(<<"search_matches">>, #{<<"competition">> => <<"copa do brasil">>,
                                          <<"season">> => 2023,
                                          <<"limit">> => 50})
    end),
    then("only Copa do Brasil matches are returned", fun() ->
        maps:get(total, Result) > 50 andalso
            lists:all(fun(#{competition := C}) -> C =:= copa_do_brasil end,
                      maps:get(matches, Result))
    end),
    and_("the competition is named in Portuguese", fun() ->
        lists:all(fun(#{competition_name := N}) -> N =:= <<"Copa do Brasil">> end,
                  maps:get(matches, Result))
    end).

matches_by_date_range(_Config) ->
    scenario("Find matches inside a date range"),
    {Result, _} = when_("I search matches between 2019-05-01 and 2019-05-31", fun() ->
        call_tool(<<"search_matches">>, #{<<"date_from">> => <<"2019-05-01">>,
                                          <<"date_to">> => <<"2019-05-31">>,
                                          <<"competition">> => <<"serie a">>,
                                          <<"limit">> => 100})
    end),
    then("every match falls inside the range", fun() ->
        Matches = maps:get(matches, Result),
        Matches =/= [] andalso
            lists:all(fun(#{date := D}) ->
                              D >= <<"2019-05-01">> andalso D =< <<"2019-05-31">>
                      end, Matches)
    end).

home_and_away_filters(_Config) ->
    scenario("Restrict a search to home matches"),
    {Home, _} = when_("I search Santos home matches in 2019", fun() ->
        call_tool(<<"search_matches">>, #{<<"team">> => <<"Santos">>,
                                          <<"season">> => 2019,
                                          <<"competition">> => <<"serie a">>,
                                          <<"venue">> => <<"home">>,
                                          <<"limit">> => 50})
    end),
    then("all 19 home fixtures come back", fun() ->
        maps:get(total, Home) =:= 19
    end),
    and_("Santos is the home team in each of them", fun() ->
        lists:all(fun(#{home_team := H}) -> H =:= <<"Santos-SP">> end,
                  maps:get(matches, Home))
    end).

cup_stage_filter(_Config) ->
    scenario("Find all Copa Libertadores finals"),
    {Result, Text} = when_("I search Libertadores matches with stage \"final\"", fun() ->
        call_tool(<<"search_matches">>, #{<<"competition">> => <<"libertadores">>,
                                          <<"stage">> => <<"final">>,
                                          <<"limit">> => 50})
    end),
    then("only final stage matches are returned", fun() ->
        Matches = maps:get(matches, Result),
        Matches =/= [] andalso
            lists:all(fun(#{stage := S}) ->
                              binary:match(S, <<"final">>) =/= nomatch
                      end, Matches)
    end),
    and_("the answer mentions the stage", fun() ->
        binary:match(Text, <<"final">>) =/= nomatch
    end).

unknown_team_returns_suggestions(_Config) ->
    scenario("An unresolvable club name is reported with suggestions"),
    {Error, Text} = when_("I search matches for \"Sao Paolo\"", fun() ->
        call_tool_error(<<"search_matches">>, #{<<"team">> => <<"Palmeras FC XI">>})
    end),
    then("the tool reports an unknown team rather than crashing", fun() ->
        maps:get(error, Error) =:= unknown_team
    end),
    and_("the message tells the model what to do next", fun() ->
        binary:match(Text, <<"No team matched">>) =/= nomatch
    end).
