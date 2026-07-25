%%%-------------------------------------------------------------------
%%% @doc Given/When/Then helpers for the Common Test suites.
%%%
%%% Context: the specification asks for BDD style scenarios.  Rather
%%% than pulling in a Gherkin parser, each Common Test case *is* a
%%% scenario: it declares its feature and scenario name and then runs
%%% labelled steps.  The labels end up in the CT HTML log, so the log
%%% reads like the feature file the specification sketches:
%%%
%%%   Feature: Match Queries
%%%     Scenario: Find matches between two teams
%%%       Given the match data is loaded
%%%       When I search for matches between "Flamengo" and "Fluminense"
%%%       Then I should receive a list of matches
%%%
%%% `when_/2' and `given/2' return the value of their step so scenarios
%%% can thread state without a state record.
%%% @end
%%%-------------------------------------------------------------------
-module(bsmcp_bdd).

-export([feature/1, scenario/1, given/2, when_/2, then/2, and_/2, but/2,
         call_tool/2, call_tool_error/2, rpc/1]).

-include_lib("common_test/include/ct.hrl").

feature(Name) ->
    ct:log("~n=== Feature: ~ts ===", [Name]),
    ok.

scenario(Name) ->
    ct:log("--- Scenario: ~ts", [Name]),
    ok.

given(Desc, Fun) -> step("Given", Desc, Fun).
when_(Desc, Fun) -> step("When", Desc, Fun).
and_(Desc, Fun) -> step("And", Desc, Fun).
but(Desc, Fun) -> step("But", Desc, Fun).

%% A Then step must evaluate to something truthy; `true' and any other
%% non-false value pass, `false' fails the scenario with the step text.
then(Desc, Fun) ->
    case step("Then", Desc, Fun) of
        false ->
            ct:fail({assertion_failed, Desc});
        Value ->
            Value
    end.

step(Keyword, Desc, Fun) ->
    ct:log("  ~s ~ts", [Keyword, Desc]),
    try
        Fun()
    catch
        Class:Reason:Stack ->
            ct:log("  !! ~s ~ts failed: ~p:~p~n~p", [Keyword, Desc, Class, Reason, Stack]),
            erlang:raise(Class, Reason, Stack)
    end.

%%--------------------------------------------------------------------
%% Tool helpers - every scenario goes through the MCP tool layer, so the
%% tests exercise argument decoding and formatting as well as the query.
%%--------------------------------------------------------------------

call_tool(Name, Args) ->
    case bsmcp_tools:call(Name, Args) of
        {ok, Structured, Text} ->
            ct:log("    tool ~ts ->~n~ts", [Name, Text]),
            {Structured, Text};
        {error, Structured, Text} ->
            ct:fail({unexpected_tool_error, Name, Structured, Text})
    end.

call_tool_error(Name, Args) ->
    case bsmcp_tools:call(Name, Args) of
        {error, Structured, Text} ->
            ct:log("    tool ~ts -> error~n~ts", [Name, Text]),
            {Structured, Text};
        {ok, Structured, _Text} ->
            ct:fail({expected_tool_error, Name, Structured})
    end.

%% Round trip a JSON-RPC request through the protocol layer.
rpc(Request) ->
    Encoded = bsmcp_json:encode(Request),
    case bsmcp_server:handle_binary(Encoded) of
        noreply ->
            noreply;
        {reply, Response} ->
            {ok, Decoded} = bsmcp_json:decode(Response),
            Decoded
    end.
