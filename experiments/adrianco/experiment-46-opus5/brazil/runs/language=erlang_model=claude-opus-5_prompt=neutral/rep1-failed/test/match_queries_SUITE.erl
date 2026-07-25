%%%-------------------------------------------------------------------
%%% @doc Feature: Match Queries
%%%
%%% Scenarios taken from the specification: find matches by team, by
%%% date range, by competition and by season, and check that every
%%% match carries date, score and competition.
%%% @end
%%%-------------------------------------------------------------------
-module(match_queries_SUITE).

-compile([export_all, nowarn_export_all]).

-include_lib("common_test/include/ct.hrl").
-include_lib("stdlib/include/assert.hrl").

all() ->
    [find_matches_between_two_teams,
     matches_of_one_team_in_a_season,
     matches_by_competition,
     matches_by_date_range,
     home_and_away_filters,
     most_recent_meeting,
     team_name_variations_resolve_to_the_same_team,
     unknown_team_is_reported_with_suggestions,
     matches_are_deduplicated_across_files,
     copa_do_brasil_finals].

init_per_suite(Config) ->
    bdd:feature("Match Queries"),
    bdd:data_is_loaded(),
    Config.

end_per_suite(_Config) -> ok.

%%--------------------------------------------------------------------
find_matches_between_two_teams(_Config) ->
    bdd:scenario("Find matches between two teams"),
    bdd:given("the match data is loaded", fun bdd:data_is_loaded/0),
    Result = bdd:'when'("I search for matches between \"Flamengo\" and \"Fluminense\"",
                        fun() ->
                                {ok, R} = br_query:find_matches(
                                            #{team => <<"Flamengo">>,
                                              opponent => <<"Fluminense">>,
                                              limit => 100}),
                                R
                        end),
    Matches = bdd:then("I should receive a list of matches",
                       fun() ->
                               #{matches := Ms, total := Total} = Result,
                               ?assert(Total > 20),
                               ?assert(length(Ms) > 20),
                               Ms
                       end),
    bdd:'and'("each match should have date, scores and competition",
              fun() ->
                      lists:foreach(
                        fun(M) ->
                                ?assertMatch(#{date := <<_/binary>>}, M),
                                ?assertMatch(#{competition := <<_/binary>>}, M),
                                ?assert(is_integer(maps:get(home_goals, M))),
                                ?assert(is_integer(maps:get(away_goals, M))),
                                ?assertMatch(#{score := <<_/binary>>}, M)
                        end, Matches)
              end),
    bdd:'and'("both teams should be in every match",
              fun() ->
                      lists:foreach(
                        fun(#{home := H, away := A}) ->
                                ?assert(lists:sort([H, A]) =:=
                                            [<<"flamengo">>, <<"fluminense">>])
                        end, Matches)
              end).

%%--------------------------------------------------------------------
matches_of_one_team_in_a_season(_Config) ->
    bdd:scenario("Find the matches a team played in one season"),
    bdd:given("the match data is loaded", fun bdd:data_is_loaded/0),
    Result = bdd:'when'("I ask what matches Palmeiras played in 2023",
                        fun() ->
                                {ok, R} = br_query:find_matches(#{team => <<"Palmeiras">>,
                                                                  season => 2023,
                                                                  limit => 200}),
                                R
                        end),
    bdd:then("every match should be from 2023 and involve Palmeiras",
             fun() ->
                     #{matches := Ms, total := Total} = Result,
                     ?assert(Total >= 38),
                     lists:foreach(
                       fun(#{season := S, home := H, away := A}) ->
                               ?assertEqual(2023, S),
                               ?assert(H =:= <<"palmeiras">> orelse A =:= <<"palmeiras">>)
                       end, Ms)
             end).

%%--------------------------------------------------------------------
matches_by_competition(_Config) ->
    bdd:scenario("Filter matches by competition"),
    bdd:given("the match data is loaded", fun bdd:data_is_loaded/0),
    Result = bdd:'when'("I search for Flamengo matches in the Libertadores",
                        fun() ->
                                {ok, R} = br_query:find_matches(
                                            #{team => <<"Flamengo">>,
                                              competition => <<"Copa Libertadores">>,
                                              limit => 100}),
                                R
                        end),
    bdd:then("every match should be a Libertadores match",
             fun() ->
                     #{matches := Ms, total := Total} = Result,
                     ?assert(Total > 20),
                     lists:foreach(fun(#{competition := C}) ->
                                           ?assertEqual(<<"libertadores">>, C)
                                   end, Ms)
             end).

%%--------------------------------------------------------------------
matches_by_date_range(_Config) ->
    bdd:scenario("Filter matches by date range"),
    bdd:given("the match data is loaded", fun bdd:data_is_loaded/0),
    Result = bdd:'when'("I search for Santos matches in the second half of 2019",
                        fun() ->
                                {ok, R} = br_query:find_matches(
                                            #{team => <<"Santos">>,
                                              date_from => <<"2019-07-01">>,
                                              date_to => <<"2019-12-31">>,
                                              limit => 100}),
                                R
                        end),
    bdd:then("every match should fall inside the range",
             fun() ->
                     #{matches := Ms} = Result,
                     ?assert(length(Ms) > 10),
                     lists:foreach(
                       fun(#{date := D}) ->
                               ?assert(D >= <<"2019-07-01">>),
                               ?assert(D =< <<"2019-12-31">>)
                       end, Ms)
             end).

%%--------------------------------------------------------------------
home_and_away_filters(_Config) ->
    bdd:scenario("Separate home fixtures from away fixtures"),
    bdd:given("the match data is loaded", fun bdd:data_is_loaded/0),
    {Home, Away} =
        bdd:'when'("I search for Corinthians home and away matches of 2022",
                   fun() ->
                           {ok, H} = br_query:find_matches(
                                       #{home_team => <<"Corinthians">>, season => 2022,
                                         competition => <<"serie a">>, limit => 100}),
                           {ok, A} = br_query:find_matches(
                                       #{away_team => <<"Corinthians">>, season => 2022,
                                         competition => <<"serie a">>, limit => 100}),
                           {H, A}
                   end),
    bdd:then("there should be 19 of each in a 20 team league season",
             fun() ->
                     ?assertEqual(19, maps:get(total, Home)),
                     ?assertEqual(19, maps:get(total, Away))
             end),
    bdd:'and'("the home fixtures should all list Corinthians as the home team",
              fun() ->
                      lists:foreach(fun(#{home := H}) ->
                                            ?assertEqual(<<"corinthians">>, H)
                                    end, maps:get(matches, Home))
              end).

%%--------------------------------------------------------------------
most_recent_meeting(_Config) ->
    bdd:scenario("When did two teams last meet?"),
    bdd:given("the match data is loaded", fun bdd:data_is_loaded/0),
    Match = bdd:'when'("I ask for the most recent Flamengo vs Corinthians match",
                       fun() ->
                               {ok, #{matches := [M | _]}} =
                                   br_query:find_matches(#{team => <<"Flamengo">>,
                                                           opponent => <<"Corinthians">>,
                                                           sort => <<"date_desc">>,
                                                           limit => 1}),
                               M
                       end),
    bdd:then("I should get one match with a score",
             fun() ->
                     ?assertMatch(#{score := <<_/binary>>}, Match),
                     ?assert(maps:get(date, Match) > <<"2020-01-01">>)
             end),
    bdd:'and'("it should be later than every other meeting",
              fun() ->
                      {ok, #{matches := All}} =
                          br_query:find_matches(#{team => <<"Flamengo">>,
                                                  opponent => <<"Corinthians">>,
                                                  limit => 500}),
                      Dates = [D || #{date := D} <- All],
                      ?assertEqual(lists:max(Dates), maps:get(date, Match))
              end).

%%--------------------------------------------------------------------
team_name_variations_resolve_to_the_same_team(_Config) ->
    bdd:scenario("Team name variations are handled"),
    bdd:given("the match data is loaded", fun bdd:data_is_loaded/0),
    Totals = bdd:'when'("I search with four spellings of the same club",
                        fun() ->
                                [begin
                                     {ok, #{total := T}} =
                                         br_query:find_matches(#{team => Name, limit => 1}),
                                     T
                                 end || Name <- [<<"Sao Paulo">>, <<"São Paulo"/utf8>>,
                                                 <<"Sao Paulo-SP">>,
                                                 <<"Sao Paulo Futebol Clube">>]]
                        end),
    bdd:then("all four should return the same number of matches",
             fun() ->
                     ?assertEqual(1, length(lists:usort(Totals))),
                     ?assert(hd(Totals) > 500)
             end).

%%--------------------------------------------------------------------
unknown_team_is_reported_with_suggestions(_Config) ->
    bdd:scenario("An unknown team produces a helpful error"),
    bdd:given("the match data is loaded", fun bdd:data_is_loaded/0),
    Error = bdd:'when'("I search for a club that does not exist",
                       fun() ->
                               {error, E} = br_query:find_matches(
                                              #{team => <<"Nonexistent Sporting Club">>}),
                               E
                       end),
    bdd:then("the error should name the problem",
             fun() ->
                     ?assertEqual(unknown_team, maps:get(code, Error)),
                     ?assertMatch(#{message := <<_/binary>>}, Error)
             end),
    bdd:'and'("a club that only appears in the player data resolves but has no matches",
              fun() ->
                      {ok, #{total := Total}} =
                          br_query:find_matches(#{team => <<"Manchester United">>}),
                      ?assertEqual(0, Total)
              end).

%%--------------------------------------------------------------------
matches_are_deduplicated_across_files(_Config) ->
    bdd:scenario("A fixture present in three files is stored once"),
    bdd:given("the match data is loaded", fun bdd:data_is_loaded/0),
    Result = bdd:'when'("I look for the Flamengo vs Ceara match of the 2019 season",
                        fun() ->
                                {ok, R} = br_query:find_matches(
                                            #{home_team => <<"Flamengo">>,
                                              away_team => <<"Ceara">>,
                                              season => 2019,
                                              competition => <<"serie a">>}),
                                R
                        end),
    bdd:then("exactly one match should be returned",
             fun() -> ?assertEqual(1, maps:get(total, Result)) end),
    bdd:'and'("it should record every file it came from",
              fun() ->
                      [#{sources := Sources}] = maps:get(matches, Result),
                      ?assert(length(Sources) >= 2)
              end).

%%--------------------------------------------------------------------
copa_do_brasil_finals(_Config) ->
    bdd:scenario("Find Copa do Brasil matches of a season"),
    bdd:given("the match data is loaded", fun bdd:data_is_loaded/0),
    Result = bdd:'when'("I search the Copa do Brasil of 2019",
                        fun() ->
                                {ok, R} = br_query:find_matches(
                                            #{competition => <<"copa do brasil">>,
                                              season => 2019, limit => 200}),
                                R
                        end),
    bdd:then("I should get that season's cup matches",
             fun() ->
                     #{total := Total, matches := Ms} = Result,
                     ?assert(Total > 100),
                     lists:foreach(fun(#{competition := C, season := S}) ->
                                           ?assertEqual(<<"copa_do_brasil">>, C),
                                           ?assertEqual(2019, S)
                                   end, Ms)
             end),
    bdd:'and'("the later rounds should be marked as stages",
              fun() ->
                      Stages = [S || #{stage := S} <- maps:get(matches, Result),
                                     S =/= null],
                      ?assert(length(Stages) > 0)
              end).
