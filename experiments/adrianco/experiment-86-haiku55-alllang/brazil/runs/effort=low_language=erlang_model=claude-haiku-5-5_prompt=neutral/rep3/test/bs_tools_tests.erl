%%% Feature: Tool calls return readable answers or helpful errors.
-module(bs_tools_tests).

-include_lib("eunit/include/eunit.hrl").
-import(bs_test_support, [u/1]).

tools_test_() ->
    {setup, fun bs_test_support:fixture_data/0, fun(_) -> ok end,
     fun(D) ->
         [{"Given two teams in a cup, When searching matches, Then the summary lists them",
           ?_test(begin
                      {ok, T} = bs_tools:call(<<"search_matches">>,
                                              #{<<"team">> => <<"Flamengo">>,
                                                <<"competition">> => <<"Copa do Brasil">>}, D),
                      ?assertMatch({_, _}, binary:match(T, <<"Matches (Copa do Brasil): 2 found">>)),
                      ?assertMatch({_, _}, binary:match(T, <<"Corinthians 0-1 Flamengo">>))
                  end)},

          {"Given a standings request without a season, When called, Then an error explains it",
           ?_assertEqual({error, <<"standings requires a season, e.g. 2023">>},
                         bs_tools:call(<<"standings">>, #{}, D))},

          {"Given an unknown team, When called, Then the error names it",
           ?_assertEqual({error, <<"No team matching 'Nowhere' in the match data.">>},
                         bs_tools:call(<<"team_stats">>, #{<<"team">> => <<"Nowhere">>}, D))},

          {"Given a malformed date, When called, Then the error names the bad value",
           ?_assertEqual({error, <<"Cannot read date 'soon' for from">>},
                         bs_tools:call(<<"search_matches">>, #{<<"from">> => <<"soon">>}, D))},

          {"Given an unknown tool name, When called, Then an error is returned",
           ?_assertEqual({error, <<"Unknown tool: nope">>}, bs_tools:call(<<"nope">>, #{}, D))},

          {"Given the catalogue, When listed, Then every tool has a JSON schema",
           ?_assertEqual(7, length([T || T <- bs_tools:list(), is_map(maps:get(inputSchema, T))]))}]
     end}.
