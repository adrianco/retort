%% MCP protocol scenarios: JSON-RPC messages in, JSON-RPC messages out.
-module(bs_mcp_tests).
-include_lib("eunit/include/eunit.hrl").

mcp_test_() ->
    {setup, fun() -> ok = bs_data:ensure_loaded() end,
     [fun initialize/0, fun notifications_get_no_reply/0, fun tools_list/0, fun tools_call/0,
      fun tool_errors/0, fun protocol_errors/0, fun batch/0]}.

rpc(Msg) ->
    {reply, Json} = bs_mcp:handle_line(iolist_to_binary(json:encode(Msg))),
    ?assertEqual(nomatch, binary:match(Json, <<"\n">>)),
    json:decode(Json).

req(Id, Method, Params) ->
    #{jsonrpc => <<"2.0">>, id => Id, method => Method, params => Params}.

initialize() ->
    R = rpc(req(1, <<"initialize">>, #{protocolVersion => <<"2025-03-26">>, capabilities => #{},
                                      clientInfo => #{name => <<"t">>, version => <<"0">>}})),
    ?assertMatch(#{<<"jsonrpc">> := <<"2.0">>, <<"id">> := 1,
                   <<"result">> := #{<<"protocolVersion">> := <<"2025-03-26">>,
                                     <<"capabilities">> := #{<<"tools">> := _},
                                     <<"serverInfo">> := #{<<"name">> := <<"brazilian-soccer-mcp">>}}}, R),
    ?assertMatch(#{<<"result">> := #{<<"protocolVersion">> := <<"2024-11-05">>}},
                 rpc(req(2, <<"initialize">>, #{protocolVersion => <<"1999-01-01">>}))),
    ?assertMatch(#{<<"id">> := <<"p">>, <<"result">> := R2} when map_size(R2) =:= 0,
                 rpc(req(<<"p">>, <<"ping">>, #{}))).

notifications_get_no_reply() ->
    ?assertEqual(noreply, bs_mcp:handle_line(<<"{\"jsonrpc\":\"2.0\",\"method\":\"notifications/initialized\"}\n">>)),
    ?assertEqual(noreply, bs_mcp:handle_line(<<"  \n">>)).

tools_list() ->
    #{<<"result">> := #{<<"tools">> := Tools}} = rpc(#{jsonrpc => <<"2.0">>, id => 3, method => <<"tools/list">>}),
    Names = [N || #{<<"name">> := N} <- Tools],
    ?assertEqual(15, length(Names)),
    [?assert(lists:member(N, Names)) || N <- [<<"search_matches">>, <<"head_to_head">>, <<"team_stats">>,
                                              <<"standings">>, <<"search_players">>, <<"biggest_wins">>]],
    [?assertMatch(#{<<"description">> := <<_, _/binary>>,
                    <<"inputSchema">> := #{<<"type">> := <<"object">>, <<"properties">> := #{},
                                           <<"required">> := Req}} when is_list(Req), T)
     || T <- Tools].

tools_call() ->
    R = rpc(req(4, <<"tools/call">>, #{name => <<"head_to_head">>,
                                       arguments => #{team_a => <<"Grêmio"/utf8>>, team_b => <<"Internacional">>}})),
    #{<<"id">> := 4, <<"result">> := #{<<"isError">> := false,
                                       <<"content">> := [#{<<"type">> := <<"text">>, <<"text">> := Text}]}} = R,
    ?assertMatch({_, _}, binary:match(Text, <<"Grêmio vs Internacional (Grenal)"/utf8>>)),
    %% arguments may be omitted
    ?assertMatch(#{<<"result">> := #{<<"isError">> := false}},
                 rpc(req(5, <<"tools/call">>, #{name => <<"data_summary">>}))).

tool_errors() ->
    ?assertMatch(#{<<"result">> := #{<<"isError">> := true, <<"content">> := [#{<<"text">> := <<"No team", _/binary>>}]}},
                 rpc(req(6, <<"tools/call">>, #{name => <<"team_stats">>, arguments => #{team => <<"Xyzzyx">>}}))),
    ?assertMatch(#{<<"error">> := #{<<"code">> := -32602}},
                 rpc(req(7, <<"tools/call">>, #{name => <<"no_such_tool">>, arguments => #{}}))),
    ?assertMatch(#{<<"error">> := #{<<"code">> := -32602}}, rpc(req(8, <<"tools/call">>, #{}))).

protocol_errors() ->
    {reply, J} = bs_mcp:handle_line(<<"{not json">>),
    ?assertMatch(#{<<"id">> := null, <<"error">> := #{<<"code">> := -32700}}, json:decode(J)),
    ?assertMatch(#{<<"id">> := 9, <<"error">> := #{<<"code">> := -32601}}, rpc(req(9, <<"bogus/method">>, #{}))),
    ?assertMatch(#{<<"error">> := #{<<"code">> := -32600}}, rpc(#{foo => 1})).

batch() ->
    {reply, J} = bs_mcp:handle_line(iolist_to_binary(json:encode(
        [req(10, <<"ping">>, #{}), #{jsonrpc => <<"2.0">>, method => <<"notifications/x">>}, req(11, <<"ping">>, #{})]))),
    ?assertMatch([#{<<"id">> := 10}, #{<<"id">> := 11}], json:decode(J)).
