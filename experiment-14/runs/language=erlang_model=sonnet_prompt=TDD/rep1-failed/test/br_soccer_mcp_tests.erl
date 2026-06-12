-module(br_soccer_mcp_tests).
-include_lib("eunit/include/eunit.hrl").

%% Test MCP request/response parsing and construction (no I/O needed).

handle_initialize_test() ->
    Req = #{<<"jsonrpc">> => <<"2.0">>, <<"id">> => 1,
            <<"method">> => <<"initialize">>,
            <<"params">> => #{<<"protocolVersion">> => <<"2024-11-05">>,
                              <<"capabilities">> => #{},
                              <<"clientInfo">> => #{<<"name">> => <<"test">>}}},
    Resp = br_soccer_mcp:handle_request(Req, #{}),
    ?assertEqual(1, maps:get(<<"id">>, Resp)),
    Result = maps:get(<<"result">>, Resp),
    ?assert(maps:is_key(<<"protocolVersion">>, Result)),
    ?assert(maps:is_key(<<"capabilities">>, Result)),
    ?assert(maps:is_key(<<"serverInfo">>, Result)).

handle_tools_list_test() ->
    Req = #{<<"jsonrpc">> => <<"2.0">>, <<"id">> => 2,
            <<"method">> => <<"tools/list">>,
            <<"params">> => #{}},
    Resp = br_soccer_mcp:handle_request(Req, #{}),
    ?assertEqual(2, maps:get(<<"id">>, Resp)),
    Result = maps:get(<<"result">>, Resp),
    Tools = maps:get(<<"tools">>, Result),
    ?assert(length(Tools) >= 5),
    Names = [maps:get(<<"name">>, T) || T <- Tools],
    ?assert(lists:member(<<"find_matches">>, Names)),
    ?assert(lists:member(<<"team_stats">>, Names)),
    ?assert(lists:member(<<"find_players">>, Names)),
    ?assert(lists:member(<<"season_standings">>, Names)),
    ?assert(lists:member(<<"head_to_head">>, Names)).

handle_unknown_method_test() ->
    Req = #{<<"jsonrpc">> => <<"2.0">>, <<"id">> => 3,
            <<"method">> => <<"unknown/method">>,
            <<"params">> => #{}},
    Resp = br_soccer_mcp:handle_request(Req, #{}),
    ?assertEqual(3, maps:get(<<"id">>, Resp)),
    ?assert(maps:is_key(<<"error">>, Resp)).

handle_notification_test() ->
    %% Notifications have no id; we should return nothing
    Req = #{<<"jsonrpc">> => <<"2.0">>,
            <<"method">> => <<"notifications/initialized">>,
            <<"params">> => #{}},
    Result = br_soccer_mcp:handle_request(Req, #{}),
    ?assertEqual(notification, Result).

encode_decode_json_test() ->
    Map = #{<<"key">> => <<"value">>, <<"num">> => 42},
    Encoded = br_soccer_mcp:encode_json(Map),
    ?assert(is_list(Encoded) orelse is_binary(Encoded)),
    Decoded = br_soccer_mcp:decode_json(Encoded),
    ?assertEqual(<<"value">>, maps:get(<<"key">>, Decoded)),
    ?assertEqual(42, maps:get(<<"num">>, Decoded)).

format_matches_output_test() ->
    Matches = [
        #{home_team => "Flamengo", away_team => "Fluminense",
          home_goal => 2, away_goal => 1, date => {2023, 9, 3},
          season => 2023, competition => "brasileirao"}
    ],
    Output = br_soccer_mcp:format_matches(Matches),
    ?assert(is_list(Output)),
    ?assert(string:find(Output, "Flamengo") =/= nomatch),
    ?assert(string:find(Output, "Fluminense") =/= nomatch),
    ?assert(string:find(Output, "2-1") =/= nomatch).

format_players_output_test() ->
    Players = [
        #{name => "Neymar Jr", overall => 92, position => "LW",
          club => "Paris Saint-Germain", nationality => "Brazil",
          age => 26, potential => 92}
    ],
    Output = br_soccer_mcp:format_players(Players),
    ?assert(string:find(Output, "Neymar") =/= nomatch),
    ?assert(string:find(Output, "92") =/= nomatch).

format_standings_output_test() ->
    Standings = [
        {"Flamengo", 90, 28, 6, 4},
        {"Santos", 74, 22, 8, 8}
    ],
    Output = br_soccer_mcp:format_standings(Standings),
    ?assert(string:find(Output, "Flamengo") =/= nomatch),
    ?assert(string:find(Output, "90") =/= nomatch),
    ?assert(string:find(Output, "Santos") =/= nomatch).
