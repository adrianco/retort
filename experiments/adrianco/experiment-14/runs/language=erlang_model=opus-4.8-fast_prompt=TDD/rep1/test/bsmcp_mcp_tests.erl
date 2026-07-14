-module(bsmcp_mcp_tests).
-include_lib("eunit/include/eunit.hrl").

store() ->
    M = #{competition => <<"Brasileirão"/utf8>>,
          home => <<"Flamengo">>, away => <<"Santos">>,
          home_norm => <<"flamengo">>, away_norm => <<"santos">>,
          home_goal => 2, away_goal => 0, season => 2019,
          round => undefined, date => <<"2019-06-01">>, stage => undefined},
    #{matches => [M], players => []}.

req(Id, Method, Params) ->
    #{<<"jsonrpc">> => <<"2.0">>, <<"id">> => Id,
      <<"method">> => Method, <<"params">> => Params}.

%% --- initialize -------------------------------------------------------

initialize_test() ->
    {reply, Resp} = bsmcp_mcp:handle_request(req(1, <<"initialize">>, #{}), store()),
    ?assertEqual(1, maps:get(<<"id">>, Resp)),
    Result = maps:get(<<"result">>, Resp),
    ?assert(maps:is_key(<<"protocolVersion">>, Result)),
    ?assert(maps:is_key(<<"serverInfo">>, Result)),
    ?assert(maps:is_key(<<"capabilities">>, Result)).

%% --- tools/list -------------------------------------------------------

tools_list_test() ->
    {reply, Resp} = bsmcp_mcp:handle_request(req(2, <<"tools/list">>, #{}), store()),
    Result = maps:get(<<"result">>, Resp),
    Tools = maps:get(<<"tools">>, Result),
    ?assert(is_list(Tools)),
    ?assert(length(Tools) >= 6).

%% --- tools/call -------------------------------------------------------

tools_call_test() ->
    Params = #{<<"name">> => <<"find_matches">>,
               <<"arguments">> => #{<<"team">> => <<"Flamengo">>}},
    {reply, Resp} = bsmcp_mcp:handle_request(req(3, <<"tools/call">>, Params), store()),
    Result = maps:get(<<"result">>, Resp),
    [Content | _] = maps:get(<<"content">>, Result),
    ?assertEqual(<<"text">>, maps:get(<<"type">>, Content)),
    ?assert(binary:match(maps:get(<<"text">>, Content), <<"Flamengo">>) =/= nomatch),
    ?assertNot(maps:get(<<"isError">>, Result, false)).

tools_call_error_sets_is_error_test() ->
    Params = #{<<"name">> => <<"head_to_head">>, <<"arguments">> => #{}},
    {reply, Resp} = bsmcp_mcp:handle_request(req(4, <<"tools/call">>, Params), store()),
    Result = maps:get(<<"result">>, Resp),
    ?assertEqual(true, maps:get(<<"isError">>, Result)).

tools_call_unknown_tool_test() ->
    Params = #{<<"name">> => <<"bogus">>, <<"arguments">> => #{}},
    {reply, Resp} = bsmcp_mcp:handle_request(req(5, <<"tools/call">>, Params), store()),
    Result = maps:get(<<"result">>, Resp),
    ?assertEqual(true, maps:get(<<"isError">>, Result)).

tools_list_json_encodable_test() ->
    %% The full catalog must round-trip through JSON (all literals valid UTF-8).
    {reply, Resp} = bsmcp_mcp:handle_request(req(2, <<"tools/list">>, #{}), store()),
    Bin = bsmcp_mcp:encode(Resp),
    Decoded = bsmcp_mcp:decode(Bin),
    Tools = maps:get(<<"tools">>, maps:get(<<"result">>, Decoded)),
    ?assert(length(Tools) >= 6).

every_response_json_encodable_test() ->
    %% A tools/call response containing accented data must encode cleanly.
    Params = #{<<"name">> => <<"find_matches">>,
               <<"arguments">> => #{<<"competition">> => <<"Brasileirão"/utf8>>,
                                    <<"season">> => 2019, <<"limit">> => 1}},
    {reply, Resp} = bsmcp_mcp:handle_request(req(9, <<"tools/call">>, Params), store()),
    ?assert(is_binary(bsmcp_mcp:encode(Resp))).

%% --- ping -------------------------------------------------------------

ping_test() ->
    {reply, Resp} = bsmcp_mcp:handle_request(req(6, <<"ping">>, #{}), store()),
    ?assertEqual(#{}, maps:get(<<"result">>, Resp)).

%% --- notifications ----------------------------------------------------

notification_no_reply_test() ->
    Note = #{<<"jsonrpc">> => <<"2.0">>,
             <<"method">> => <<"notifications/initialized">>},
    ?assertEqual(noreply, bsmcp_mcp:handle_request(Note, store())).

%% --- unknown method ---------------------------------------------------

unknown_method_test() ->
    {reply, Resp} = bsmcp_mcp:handle_request(req(7, <<"frobnicate">>, #{}), store()),
    Error = maps:get(<<"error">>, Resp),
    ?assertEqual(-32601, maps:get(<<"code">>, Error)).

%% --- JSON round trip via stdio framing --------------------------------

encode_decode_roundtrip_test() ->
    Resp = #{<<"jsonrpc">> => <<"2.0">>, <<"id">> => 1,
             <<"result">> => #{<<"ok">> => true}},
    Bin = bsmcp_mcp:encode(Resp),
    ?assert(is_binary(Bin)),
    Decoded = bsmcp_mcp:decode(Bin),
    ?assertEqual(1, maps:get(<<"id">>, Decoded)).

decode_handles_utf8_test() ->
    Bin = bsmcp_mcp:encode(#{<<"name">> => <<"São Paulo"/utf8>>}),
    Decoded = bsmcp_mcp:decode(Bin),
    ?assertEqual(<<"São Paulo"/utf8>>, maps:get(<<"name">>, Decoded)).
