%%% Feature: The MCP stdio protocol answers clients correctly.
-module(bs_mcp_tests).

-include_lib("eunit/include/eunit.hrl").
-import(bs_test_support, [u/1]).

%% Sends one JSON-RPC line and decodes the reply (no_reply passes through).
call(Line, Data) ->
    case bs_mcp:handle_line(unicode:characters_to_binary(Line), Data) of
        no_reply -> no_reply;
        Reply -> json:decode(Reply)
    end.

mcp_test_() ->
    {setup, fun bs_test_support:fixture_data/0, fun(_) -> ok end,
     fun(D) ->
         [{"Given an initialize request, When handled, Then the protocol version and server name are returned",
           ?_test(begin
                      #{<<"result">> := R} = call(<<"{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\"}">>, D),
                      ?assertEqual(<<"2024-11-05">>, maps:get(<<"protocolVersion">>, R)),
                      ?assertEqual(<<"brazilian-soccer-mcp">>,
                                   maps:get(<<"name">>, maps:get(<<"serverInfo">>, R)))
                  end)},

          {"Given a notification without an id, When handled, Then no reply is sent",
           ?_assertEqual(no_reply,
                         call(<<"{\"jsonrpc\":\"2.0\",\"method\":\"notifications/initialized\"}">>, D))},

          {"Given a blank line, When handled, Then no reply is sent",
           ?_assertEqual(no_reply, call(<<"   ">>, D))},

          {"Given a tools/list request, When handled, Then all seven tools are advertised",
           ?_test(begin
                      #{<<"result">> := #{<<"tools">> := Tools}} =
                          call(<<"{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/list\"}">>, D),
                      Names = [maps:get(<<"name">>, T) || T <- Tools],
                      ?assertEqual(7, length(Names)),
                      ?assert(lists:member(<<"standings">>, Names))
                  end)},

          {"Given a tools/call with accented output, When handled, Then UTF-8 survives the round trip",
           ?_test(begin
                      Line = <<"{\"jsonrpc\":\"2.0\",\"id\":3,\"method\":\"tools/call\","
                               "\"params\":{\"name\":\"standings\",\"arguments\":{\"season\":2019}}}">>,
                      #{<<"result">> := R} = call(Line, D),
                      [#{<<"text">> := Text}] = maps:get(<<"content">>, R),
                      ?assertMatch({_, _}, binary:match(Text, u("Brasileirão Série A 2019"))),
                      ?assertEqual(false, maps:get(<<"isError">>, R))
                  end)},

          {"Given a tool failure, When handled, Then isError is set so the model can retry",
           ?_test(begin
                      Line = <<"{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"tools/call\","
                               "\"params\":{\"name\":\"team_stats\",\"arguments\":{\"team\":\"Nobody\"}}}">>,
                      #{<<"result">> := R} = call(Line, D),
                      ?assertEqual(true, maps:get(<<"isError">>, R))
                  end)},

          {"Given malformed JSON, When handled, Then a parse error is returned",
           ?_test(begin
                      #{<<"error">> := E} = call(<<"{not json">>, D),
                      ?assertEqual(-32700, maps:get(<<"code">>, E))
                  end)},

          {"Given an unknown method, When handled, Then method-not-found is returned",
           ?_test(begin
                      #{<<"error">> := E} = call(<<"{\"jsonrpc\":\"2.0\",\"id\":5,\"method\":\"nope\"}">>, D),
                      ?assertEqual(-32601, maps:get(<<"code">>, E))
                  end)},

          {"Given a ping, When handled, Then an empty result is returned",
           ?_assertEqual(#{<<"jsonrpc">> => <<"2.0">>, <<"id">> => 6, <<"result">> => #{}},
                         call(<<"{\"jsonrpc\":\"2.0\",\"id\":6,\"method\":\"ping\"}">>, D))}]
     end}.
