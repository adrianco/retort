-module(br_soccer_mcp_server_tests).
-include_lib("eunit/include/eunit.hrl").

%% TDD Cycle 1: Process a single JSON-RPC line
process_line_initialize_test() ->
    Data = empty_data(),
    Req = <<"{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\","
            "\"params\":{\"protocolVersion\":\"2024-11-05\","
            "\"capabilities\":{},\"clientInfo\":{\"name\":\"test\"}}}">>,
    {ok, RespBin} = br_soccer_mcp_server:process_line(Req, Data),
    Resp = jsx:decode(RespBin, [return_maps]),
    ?assertEqual(<<"2.0">>, maps:get(<<"jsonrpc">>, Resp)),
    ?assertEqual(1, maps:get(<<"id">>, Resp)),
    ?assert(maps:is_key(<<"result">>, Resp)).

%% TDD Cycle 2: Process tools/list
process_line_tools_list_test() ->
    Data = empty_data(),
    Req = <<"{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/list\",\"params\":{}}">>,
    {ok, RespBin} = br_soccer_mcp_server:process_line(Req, Data),
    Resp = jsx:decode(RespBin, [return_maps]),
    Result = maps:get(<<"result">>, Resp),
    Tools = maps:get(<<"tools">>, Result),
    ?assert(length(Tools) >= 5).

%% TDD Cycle 3: Notification (no id) returns no_response
process_notification_test() ->
    Data = empty_data(),
    Req = <<"{\"jsonrpc\":\"2.0\",\"method\":\"initialized\",\"params\":{}}">>,
    Result = br_soccer_mcp_server:process_line(Req, Data),
    ?assertEqual(no_response, Result).

%% TDD Cycle 4: Malformed JSON returns parse error
process_malformed_json_test() ->
    Data = empty_data(),
    Req = <<"not valid json">>,
    {ok, RespBin} = br_soccer_mcp_server:process_line(Req, Data),
    Resp = jsx:decode(RespBin, [return_maps]),
    ?assert(maps:is_key(<<"error">>, Resp)),
    Err = maps:get(<<"error">>, Resp),
    ?assertEqual(-32700, maps:get(<<"code">>, Err)).

%% TDD Cycle 5: tools/call with real data loaded from files
process_search_matches_test() ->
    DataDir = filename:join([filename:absname("data"), "kaggle"]),
    Data = br_soccer_data:load_all(DataDir),
    Req = <<"{\"jsonrpc\":\"2.0\",\"id\":5,\"method\":\"tools/call\","
            "\"params\":{\"name\":\"search_matches\","
            "\"arguments\":{\"team\":\"Flamengo\",\"season\":\"2023\",\"limit\":5}}}">>,
    {ok, RespBin} = br_soccer_mcp_server:process_line(Req, Data),
    Resp = jsx:decode(RespBin, [return_maps]),
    Result = maps:get(<<"result">>, Resp),
    Content = maps:get(<<"content">>, Result),
    Text = maps:get(<<"text">>, hd(Content)),
    ?assert(binary:match(Text, <<"Flamengo">>) =/= nomatch).

%% TDD Cycle 6: competition_standings with real data
process_standings_test() ->
    DataDir = filename:join([filename:absname("data"), "kaggle"]),
    Data = br_soccer_data:load_all(DataDir),
    Req = <<"{\"jsonrpc\":\"2.0\",\"id\":6,\"method\":\"tools/call\","
            "\"params\":{\"name\":\"competition_standings\","
            "\"arguments\":{\"competition\":\"brasileirao\",\"season\":\"2019\"}}}">>,
    {ok, RespBin} = br_soccer_mcp_server:process_line(Req, Data),
    Resp = jsx:decode(RespBin, [return_maps]),
    Result = maps:get(<<"result">>, Resp),
    Content = maps:get(<<"content">>, Result),
    Text = maps:get(<<"text">>, hd(Content)),
    %% 2019 Brasileirao champion was Flamengo
    ?assert(binary:match(Text, <<"Flamengo">>) =/= nomatch).

empty_data() ->
    #{brasileirao => [], copa_brasil => [], libertadores => [],
      br_football => [], historical => [], players => []}.
