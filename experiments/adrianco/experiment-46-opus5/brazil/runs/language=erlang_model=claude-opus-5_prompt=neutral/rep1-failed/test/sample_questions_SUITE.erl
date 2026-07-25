%%%-------------------------------------------------------------------
%%% @doc Feature: Sample questions and query performance
%%%
%%% The specification asks for at least 20 answerable sample questions,
%%% simple lookups under 2 seconds and aggregate queries under 5.  This
%%% suite runs every question from {@link br_samples} through the same
%%% path an LLM would use (the `ask' tool), checks that the answer is
%%% real, and times it.
%%% @end
%%%-------------------------------------------------------------------
-module(sample_questions_SUITE).

-compile([export_all, nowarn_export_all]).

-include_lib("common_test/include/ct.hrl").
-include_lib("stdlib/include/assert.hrl").

-define(SIMPLE_LIMIT_MS, 2000).
-define(AGGREGATE_LIMIT_MS, 5000).

all() ->
    [at_least_twenty_sample_questions,
     every_sample_question_is_answered,
     answers_contain_the_expected_facts,
     questions_are_routed_to_the_right_tool,
     simple_lookups_are_fast,
     aggregate_queries_are_fast,
     the_same_question_phrased_differently].

init_per_suite(Config) ->
    bdd:feature("Sample questions"),
    bdd:data_is_loaded(),
    Config.

end_per_suite(_Config) -> ok.

%%--------------------------------------------------------------------
at_least_twenty_sample_questions(_Config) ->
    bdd:scenario("The server ships with a set of answerable questions"),
    bdd:given("the data is loaded", fun bdd:data_is_loaded/0),
    bdd:then("there should be at least 20 of them",
             fun() -> ?assert(br_samples:count() >= 20) end).

%%--------------------------------------------------------------------
every_sample_question_is_answered(_Config) ->
    bdd:scenario("Every sample question produces an answer"),
    bdd:given("the data is loaded", fun bdd:data_is_loaded/0),
    Answers = bdd:'when'("I ask each question through the ask tool",
                         fun() ->
                                 [{Q, ask(Q)} || Q <- br_samples:questions()]
                         end),
    bdd:then("none of them should fail",
             fun() ->
                     Failed = [{Q, A} || {Q, A} <- Answers, not is_answer(A)],
                     ?assertEqual([], Failed)
             end),
    bdd:'and'("each answer should be substantial text",
              fun() ->
                      lists:foreach(
                        fun({Q, #{answer := Text}}) ->
                                ct:log("~ts~n~ts", [Q, Text]),
                                ?assert(byte_size(Text) > 30)
                        end, Answers)
              end).

%%--------------------------------------------------------------------
answers_contain_the_expected_facts(_Config) ->
    bdd:scenario("Answers contain the facts they should"),
    bdd:given("the data is loaded", fun bdd:data_is_loaded/0),
    Expectations =
        [{<<"Who won the 2019 Brasileirao?">>, [<<"Flamengo">>, <<"90 pts">>]},
         {<<"Which teams were relegated in 2020?">>, [<<"Relegated">>]},
         {<<"Show me all Flamengo vs Fluminense matches">>,
          [<<"Fla-Flu">>, <<"Head-to-head">>]},
         {<<"What is Corinthians' home record in 2022?">>,
          [<<"Corinthians home record">>, <<"Win rate">>]},
         {<<"Who is Neymar?">>, [<<"Neymar">>, <<"Overall: 92">>]},
         {<<"What's the average goals per match in the Brasileirao?">>,
          [<<"average">>, <<"Home win rate">>]},
         {<<"Show me all derbies in 2023">>, [<<"Gre-Nal">>, <<"Derby Paulista"/utf8>>]},
         {<<"Which team scored the most goals in Serie A 2023?">>, [<<"goals">>]},
         {<<"Find all Brazilian players in the dataset">>, [<<"Overall">>]},
         {<<"What competitions has Palmeiras played in?">>,
          [<<"Copa Libertadores">>, <<"Copa do Brasil">>]}],
    bdd:then("each answer mentions the expected facts",
             fun() ->
                     lists:foreach(
                       fun({Question, Needles}) ->
                               #{answer := Text} = ask(Question),
                               lists:foreach(
                                 fun(Needle) ->
                                         ?assertEqual({Question, Needle, found},
                                                      {Question, Needle,
                                                       case binary:match(Text, Needle) of
                                                           nomatch -> Text;
                                                           _ -> found
                                                       end})
                                 end, Needles)
                       end, Expectations)
             end).

%%--------------------------------------------------------------------
questions_are_routed_to_the_right_tool(_Config) ->
    bdd:scenario("The router picks a sensible tool for each question"),
    bdd:given("the data is loaded", fun bdd:data_is_loaded/0),
    Expected =
        [{<<"Who won the 2019 Brasileirao?">>, <<"standings">>},
         {<<"Which teams were relegated in 2020?">>, <<"standings">>},
         {<<"Compare Palmeiras and Santos head to head">>, <<"head_to_head">>},
         {<<"What is Corinthians' home record in 2022?">>, <<"team_stats">>},
         {<<"What competitions has Palmeiras played in?">>, <<"team_profile">>},
         {<<"Who is Neymar?">>, <<"player_profile">>},
         {<<"Which players play for Cruzeiro?">>, <<"club_squad">>},
         {<<"Show me all derbies in 2023">>, <<"derbies">>},
         {<<"Which team has the best away record?">>, <<"team_rankings">>},
         {<<"What's the average goals per match in the Brasileirao?">>,
          <<"competition_stats">>},
         {<<"Show me the biggest wins in the dataset">>, <<"biggest_wins">>},
         {<<"Compare the 2018 and 2019 seasons">>, <<"compare_seasons">>},
         {<<"What matches did Palmeiras play in 2023?">>, <<"search_matches">>},
         {<<"What data sets are loaded?">>, <<"dataset_summary">>}],
    bdd:then("the plan for each question names that tool",
             fun() ->
                     lists:foreach(
                       fun({Question, Tool}) ->
                               #{tool := Chosen} = br_nl:plan(Question),
                               ?assertEqual({Question, Tool}, {Question, Chosen})
                       end, Expected)
             end),
    bdd:'and'("the season and competition are extracted from the question",
              fun() ->
                      #{arguments := Args} = br_nl:plan(<<"Who won the 2019 Brasileirao?">>),
                      ?assertEqual(2019, maps:get(season, Args)),
                      ?assertEqual(<<"brasileirao_serie_a">>, maps:get(competition, Args))
              end),
    bdd:'and'("the teams are extracted from the question",
              fun() ->
                      #{arguments := Args} =
                          br_nl:plan(<<"Show me all Flamengo vs Fluminense matches">>),
                      ?assertEqual(<<"flamengo">>, maps:get(team_a, Args)),
                      ?assertEqual(<<"fluminense">>, maps:get(team_b, Args))
              end),
    bdd:'and'("a derby can be named instead of the two clubs",
              fun() ->
                      #{tool := Tool, arguments := Args} =
                          br_nl:plan(<<"What was the score in the last Gre-Nal?">>),
                      ?assertEqual(<<"search_matches">>, Tool),
                      ?assertEqual(1, maps:get(limit, Args)),
                      ?assertEqual(lists:sort([<<"gremio">>, <<"internacional">>]),
                                   lists:sort([maps:get(team, Args),
                                               maps:get(opponent, Args)])),
                      #{tool := FlaFlu} = br_nl:plan(<<"Show the Fla-Flu matches of 2019">>),
                      ?assertEqual(<<"head_to_head">>, FlaFlu)
              end).

%%--------------------------------------------------------------------
simple_lookups_are_fast(_Config) ->
    bdd:scenario("Simple lookups respond in under two seconds"),
    bdd:given("the data is loaded", fun bdd:data_is_loaded/0),
    Timings = bdd:'when'("I time a handful of simple lookups",
                         fun() ->
                                 [{Label, time_ms(F)}
                                  || {Label, F} <-
                                         [{"match lookup",
                                           fun() -> br_query:find_matches(
                                                      #{team => <<"Flamengo">>,
                                                        opponent => <<"Corinthians">>,
                                                        limit => 5}) end},
                                          {"player lookup",
                                           fun() -> br_query:player_profile(
                                                      #{name => <<"Neymar">>}) end},
                                          {"team stats",
                                           fun() -> br_query:team_stats(
                                                      #{team => <<"Santos">>,
                                                        season => 2019}) end},
                                          {"graph neighbours",
                                           fun() -> br_query:graph_neighbors(
                                                      #{node => <<"team:santos">>,
                                                        limit => 20}) end}]]
                         end),
    bdd:then("each of them should be well under the two second budget",
             fun() ->
                     ct:log("~p", [Timings]),
                     lists:foreach(fun({Label, Ms}) ->
                                           ?assertEqual({Label, true},
                                                        {Label, Ms < ?SIMPLE_LIMIT_MS})
                                   end, Timings)
             end).

%%--------------------------------------------------------------------
aggregate_queries_are_fast(_Config) ->
    bdd:scenario("Aggregate queries respond in under five seconds"),
    bdd:given("the data is loaded", fun bdd:data_is_loaded/0),
    Timings = bdd:'when'("I time the aggregate queries",
                         fun() ->
                                 [{Label, time_ms(F)}
                                  || {Label, F} <-
                                         [{"standings",
                                           fun() -> br_query:standings(#{season => 2019}) end},
                                          {"competition stats over everything",
                                           fun() -> br_query:competition_stats(#{}) end},
                                          {"team rankings",
                                           fun() -> br_query:team_rankings(
                                                      #{venue => <<"away">>}) end},
                                          {"biggest wins",
                                           fun() -> br_query:biggest_wins(#{limit => 20}) end},
                                          {"players by club",
                                           fun() -> br_query:player_club_summary(
                                                      #{nationality => <<"Brazil">>}) end},
                                          {"derbies of a season",
                                           fun() -> br_query:derbies(#{season => 2019}) end}]]
                         end),
    bdd:then("each of them should be within the five second budget",
             fun() ->
                     ct:log("~p", [Timings]),
                     lists:foreach(fun({Label, Ms}) ->
                                           ?assertEqual({Label, true},
                                                        {Label, Ms < ?AGGREGATE_LIMIT_MS})
                                   end, Timings)
             end),
    bdd:'and'("every sample question should also stay inside the budget",
              fun() ->
                      Slow = [{Q, Ms}
                              || Q <- br_samples:questions(),
                                 Ms <- [time_ms(fun() -> br_nl:answer(Q) end)],
                                 Ms >= ?AGGREGATE_LIMIT_MS],
                      ?assertEqual([], Slow)
              end).

%%--------------------------------------------------------------------
the_same_question_phrased_differently(_Config) ->
    bdd:scenario("Different phrasings of one question give the same answer"),
    bdd:given("the data is loaded", fun bdd:data_is_loaded/0),
    Answers = bdd:'when'("I ask who won the 2019 league in three ways",
                         fun() ->
                                 [maps:get(answer, ask(Q))
                                  || Q <- [<<"Who won the 2019 Brasileirao?">>,
                                           <<"Show the 2019 Brasileirao standings">>,
                                           <<"What was the final table of the 2019 "
                                             "campeonato brasileiro?">>]]
                         end),
    bdd:then("all three should give the same table",
             fun() -> ?assertEqual(1, length(lists:usort(Answers))) end).

%%====================================================================
%% Helpers
%%====================================================================

%% Ask the way a model does: through the MCP tool, which turns a failed
%% lookup into a written answer rather than an error.
ask(Question) ->
    case br_mcp_tools:invoke(<<"ask">>, #{question => Question}) of
        {ok, Answer} -> Answer;
        {error, Error} -> {failed, Error}
    end.

is_answer(#{answer := <<_/binary>>}) -> true;
is_answer(_) -> false.

time_ms(Fun) ->
    {Micros, _} = timer:tc(Fun),
    Micros / 1000.
