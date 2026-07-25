%%%-------------------------------------------------------------------
%%% @doc Given/When/Then helpers for the acceptance suites.
%%%
%%% Every scenario reads like the Gherkin in the specification and the
%%% steps are printed to the Common Test log, so a failing run shows
%%% which step broke:
%%%
%%% ```
%%% Feature: Match Queries
%%%   Scenario: Find matches between two teams
%%%     Given the match data is loaded
%%%     When I search for matches between "Flamengo" and "Fluminense"
%%%     Then I should receive a list of matches
%%%     And each match should have date, scores and competition
%%% '''
%%% @end
%%%-------------------------------------------------------------------
-module(bdd).

-export([feature/1,
         scenario/1,
         given/2,
         'when'/2,
         then/2,
         'and'/2,
         but/2,
         data_is_loaded/0]).

-define(STEP(Keyword, Description, Fun), step(Keyword, Description, Fun)).

%%--------------------------------------------------------------------
-spec feature(iodata()) -> ok.
feature(Name) -> ct:log("~n=== Feature: ~ts ===", [Name]).

-spec scenario(iodata()) -> ok.
scenario(Name) -> ct:log("~n  Scenario: ~ts", [Name]).

-spec given(iodata(), fun(() -> T)) -> T.
given(Description, Fun) -> ?STEP("Given", Description, Fun).

-spec 'when'(iodata(), fun(() -> T)) -> T.
'when'(Description, Fun) -> ?STEP("When", Description, Fun).

-spec then(iodata(), fun(() -> T)) -> T.
then(Description, Fun) -> ?STEP("Then", Description, Fun).

-spec 'and'(iodata(), fun(() -> T)) -> T.
'and'(Description, Fun) -> ?STEP("And", Description, Fun).

-spec but(iodata(), fun(() -> T)) -> T.
but(Description, Fun) -> ?STEP("But", Description, Fun).

step(Keyword, Description, Fun) ->
    ct:log("    ~s ~ts", [Keyword, Description]),
    try
        Fun()
    catch
        Class:Reason:Stack ->
            ct:pal("    !! ~s ~ts~n       ~p:~p~n~p",
                   [Keyword, Description, Class, Reason, Stack]),
            ct:fail({step_failed, iolist_to_binary([Keyword, " ", Description]),
                     Class, Reason})
    end.

%%--------------------------------------------------------------------
%% @doc The shared background step: the data sets are in memory.
-spec data_is_loaded() -> ok.
data_is_loaded() ->
    case br_store:loaded() of
        true -> ok;
        false ->
            case br_store:ensure_loaded() of
                ok -> ok;
                {error, Reason} -> ct:fail({data_not_loaded, Reason})
            end
    end.
