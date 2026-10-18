%% Feature: MCP protocol handling and tool calls
-module(soccer_mcp_tests).
-include_lib("eunit/include/eunit.hrl").

data() ->
    #{matches => [#{source => test, date => 20230903, season => 2023,
                    competition => <<"Brasileirão Série A"/utf8>>, stage => <<"Round 22">>, round => 22,
                    home => <<"Flamengo">>, away => <<"Fluminense">>,
                    home_tokens => [<<"flamengo">>], away_tokens => [<<"fluminense">>],
                    home_goals => 2, away_goals => 1}],
      players => []}.

call(Method, Params) ->
    soccer_mcp:handle(#{<<"jsonrpc">> => <<"2.0">>, <<"id">> => 1,
                        <<"method">> => Method, <<"params">> => Params}, data()).

%% Scenario: initialize handshake
%%   Given a client starts a session
%%   When it sends initialize
%%   Then the server reports the protocol version and tools capability
initialize_test() ->
    #{result := R} = soccer_mcp:handle(#{<<"id">> => 1, <<"method">> => <<"initialize">>}, data()),
    ?assertEqual(<<"2024-11-05">>, maps:get(protocolVersion, R)),
    ?assert(is_map_key(tools, maps:get(capabilities, R))).

%% Scenario: notifications get no reply
%%   Given the client sends notifications/initialized
%%   When the server handles it
%%   Then no response is produced
notification_has_no_reply_test() ->
    ?assertEqual(no_reply, soccer_mcp:handle(#{<<"method">> => <<"notifications/initialized">>}, data())).

%% Scenario: tool discovery
%%   Given the server is running
%%   When the client asks for tools
%%   Then every tool has a name and an input schema
tools_list_test() ->
    #{result := #{tools := Tools}} = call(<<"tools/list">>, #{}),
    Names = [maps:get(name, T) || T <- Tools],
    [?assert(lists:member(N, Names)) || N <- [<<"search_matches">>, <<"team_record">>,
                                              <<"head_to_head">>, <<"search_players">>]],
    [?assert(is_map(maps:get(inputSchema, T))) || T <- Tools].

%% Scenario: a match search through tools/call
%%   Given a Flamengo vs Fluminense match in the data
%%   When the client calls search_matches for Flamengo
%%   Then the text reply contains the score and competition
search_matches_tool_test() ->
    #{result := R} = call(<<"tools/call">>,
                          #{<<"name">> => <<"search_matches">>,
                            <<"arguments">> => #{<<"team">> => <<"Flamengo">>}}),
    [#{text := Text}] = maps:get(content, R),
    ?assertEqual(false, maps:get(isError, R)),
    ?assertMatch({_, _}, binary:match(Text, <<"Flamengo 2-1 Fluminense">>)).

%% Scenario: missing required argument
%%   Given team_record needs a team
%%   When the client calls it without one
%%   Then the reply is a tool error, not a protocol error
missing_argument_test() ->
    #{result := R} = call(<<"tools/call">>, #{<<"name">> => <<"team_record">>, <<"arguments">> => #{}}),
    ?assertEqual(true, maps:get(isError, R)).

%% Scenario: unknown method
%%   Given a client calls a method the server does not implement
%%   When the server handles it
%%   Then it returns a method-not-found error with the request id
unknown_method_test() ->
    #{error := E, id := 1} = call(<<"resources/list">>, #{}),
    ?assertEqual(-32601, maps:get(code, E)).
