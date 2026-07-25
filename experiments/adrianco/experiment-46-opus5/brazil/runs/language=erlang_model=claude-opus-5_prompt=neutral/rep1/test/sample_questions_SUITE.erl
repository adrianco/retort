%%%-------------------------------------------------------------------
%%% @doc Feature: Sample questions and query performance.
%%%
%%% Context: the specification's success criteria ask that at least 20
%%% sample questions can be answered, that simple lookups return in
%%% under 2 seconds and aggregates in under 5, and that cross-file
%%% queries work.  The question list lives in {@link
%%% bsmcp_test_helper:sample_questions/0}; this suite runs every one of
%%% them through the tool layer, checks the answer and records the
%%% latency in the CT log.
%%% @end
%%%-------------------------------------------------------------------
-module(sample_questions_SUITE).

-compile([export_all, nowarn_export_all]).

-include_lib("common_test/include/ct.hrl").
-include_lib("stdlib/include/assert.hrl").

-import(bsmcp_bdd, [feature/1, scenario/1, given/2, when_/2, then/2, and_/2,
                    call_tool/2]).

-define(SIMPLE_LIMIT_MS, 2000).
-define(AGGREGATE_LIMIT_MS, 5000).

all() ->
    [at_least_twenty_questions_are_answered,
     simple_lookups_are_fast,
     aggregate_queries_are_fast,
     cross_file_queries_work,
     repeated_queries_stay_fast].

init_per_suite(Config) ->
    bsmcp_test_helper:start(),
    Config.

end_per_suite(_Config) ->
    ok.

init_per_testcase(_Case, Config) ->
    feature("Sample questions and performance"),
    Config.

%%--------------------------------------------------------------------

at_least_twenty_questions_are_answered(_Config) ->
    scenario("Every sample question produces a correct answer"),
    Questions = given("a list of natural language questions", fun() ->
        bsmcp_test_helper:sample_questions()
    end),
    then("there are at least twenty of them", fun() -> length(Questions) >= 20 end),
    Results = when_("I answer each one through its tool", fun() ->
        [begin
             T0 = erlang:monotonic_time(microsecond),
             {Structured, Text} = call_tool(Tool, Args),
             Micros = erlang:monotonic_time(microsecond) - T0,
             ct:log("  ~ts~n    -> ~ts (~.1f ms via ~ts)",
                    [Question, first_line(Text), Micros / 1000, Tool]),
             {Question, Check(Structured), Micros, Text}
         end || {Question, Tool, Args, Check} <- Questions]
    end),
    then("every question is answered correctly", fun() ->
        Failed = [Q || {Q, false, _, _} <- Results],
        case Failed of
            [] -> true;
            _ -> ct:pal("unanswered: ~p", [Failed]), false
        end
    end),
    and_("every answer includes readable text", fun() ->
        lists:all(fun({_, _, _, Text}) -> byte_size(Text) > 20 end, Results)
    end),
    and_("every answer is well inside the 5 second budget", fun() ->
        Slow = [{Q, M / 1000} || {Q, _, M, _} <- Results, M > ?AGGREGATE_LIMIT_MS * 1000],
        Slow =:= []
    end).

simple_lookups_are_fast(_Config) ->
    scenario("Simple lookups respond in under 2 seconds"),
    Timings = when_("I time a set of simple lookups", fun() ->
        [time_call(Tool, Args)
         || {Tool, Args} <-
                [{<<"search_matches">>, #{<<"team">> => <<"Flamengo">>,
                                          <<"opponent">> => <<"Fluminense">>}},
                 {<<"team_stats">>, #{<<"team">> => <<"Corinthians">>,
                                      <<"season">> => 2022}},
                 {<<"player_profile">>, #{<<"name">> => <<"Neymar">>}},
                 {<<"list_teams">>, #{<<"query">> => <<"Botafogo">>}},
                 {<<"standings">>, #{<<"competition">> => <<"serie a">>,
                                     <<"season">> => 2019}}]]
    end),
    then("each one is under two seconds", fun() ->
        lists:all(fun({_, Micros}) -> Micros < ?SIMPLE_LIMIT_MS * 1000 end, Timings)
    end),
    and_("in practice they are milliseconds", fun() ->
        Worst = lists:max([M || {_, M} <- Timings]),
        ct:log("  slowest simple lookup: ~.1f ms", [Worst / 1000]),
        Worst < 500 * 1000
    end).

aggregate_queries_are_fast(_Config) ->
    scenario("Aggregate queries respond in under 5 seconds"),
    Timings = when_("I time the heaviest aggregates", fun() ->
        [time_call(Tool, Args)
         || {Tool, Args} <-
                [{<<"competition_stats">>, #{}},
                 {<<"biggest_wins">>, #{<<"limit">> => 50}},
                 {<<"league_leaderboard">>, #{<<"metric">> => <<"points">>,
                                              <<"competition">> => <<"serie a">>}},
                 {<<"club_ratings">>, #{<<"min_players">> => 1, <<"limit">> => 100}},
                 {<<"search_players">>, #{<<"min_overall">> => 60,
                                          <<"limit">> => 200}}]]
    end),
    then("each one is under five seconds", fun() ->
        lists:all(fun({_, Micros}) -> Micros < ?AGGREGATE_LIMIT_MS * 1000 end, Timings)
    end),
    and_("the worst case is logged", fun() ->
        Worst = lists:max([M || {_, M} <- Timings]),
        ct:log("  slowest aggregate: ~.1f ms", [Worst / 1000]),
        Worst < ?AGGREGATE_LIMIT_MS * 1000
    end).

cross_file_queries_work(_Config) ->
    scenario("A question spanning the player file and the match files"),
    {Squad, _} = when_("I take a club that exists in both datasets", fun() ->
        call_tool(<<"club_squad">>, #{<<"club">> => <<"Cruzeiro">>, <<"limit">> => 3})
    end),
    TeamId = maps:get(id, maps:get(team, Squad)),
    {Profile, _} = and_("I look the same club up in the match graph", fun() ->
        call_tool(<<"team_profile">>, #{<<"team">> => <<"Cruzeiro">>})
    end),
    then("the two datasets agree on the club identity", fun() ->
        maps:get(id, maps:get(team, Profile)) =:= TeamId
    end),
    and_("the club has both a squad and a match record", fun() ->
        maps:get(squad_size, Profile) > 0
            andalso maps:get(played, maps:get(record, Profile)) > 100
    end),
    {Ratings, _} = and_("I group Brazilian players by club", fun() ->
        call_tool(<<"club_ratings">>, #{<<"nationality">> => <<"Brazil">>,
                                        <<"brazilian_clubs_only">> => true,
                                        <<"limit">> => 50})
    end),
    then("every listed club also appears in the match data", fun() ->
        lists:all(fun(C) -> maps:get(team, C) =/= undefined end,
                  maps:get(clubs, Ratings))
    end).

repeated_queries_stay_fast(_Config) ->
    scenario("Repeated queries do not degrade"),
    Micros = when_("I run one hundred lookups in a row", fun() ->
        T0 = erlang:monotonic_time(microsecond),
        lists:foreach(fun(N) ->
                              Season = 2003 + (N rem 20),
                              call_tool_quiet(<<"team_stats">>,
                                              #{<<"team">> => <<"Palmeiras">>,
                                                <<"season">> => Season})
                      end, lists:seq(1, 100)),
        erlang:monotonic_time(microsecond) - T0
    end),
    then("the whole batch takes less than five seconds", fun() ->
        ct:log("  100 lookups in ~.1f ms (~.2f ms each)", [Micros / 1000, Micros / 100000]),
        Micros < ?AGGREGATE_LIMIT_MS * 1000
    end).

%%--------------------------------------------------------------------

time_call(Tool, Args) ->
    T0 = erlang:monotonic_time(microsecond),
    call_tool_quiet(Tool, Args),
    {Tool, erlang:monotonic_time(microsecond) - T0}.

call_tool_quiet(Tool, Args) ->
    case bsmcp_tools:call(Tool, Args) of
        {ok, S, _} -> S;
        {error, S, _} -> ct:fail({tool_error, Tool, S})
    end.

first_line(Text) ->
    case binary:split(Text, <<"\n">>) of
        [Line | _] -> Line;
        _ -> Text
    end.
