%% Protocol-level tests: JSON-RPC requests in, JSON-RPC responses out.
-module(bsm_mcp_tests).
-include_lib("eunit/include/eunit.hrl").

setup() ->
    Dir = case os:getenv("BSM_DATA_DIR") of
              false -> "data/kaggle";
              D -> D
          end,
    bsm_store:load(Dir).

rpc(Map) -> json:decode(bsm_mcp:handle_line(iolist_to_binary(json:encode(Map)))).

call(Name, Args) ->
    #{<<"result">> := #{<<"content">> := [#{<<"text">> := Text}], <<"isError">> := IsError}} =
        rpc(#{jsonrpc => <<"2.0">>, id => 1, method => <<"tools/call">>,
              params => #{name => Name, arguments => Args}}),
    %% Tool errors are plain text; successful results are JSON documents.
    case IsError of
        true -> {true, Text};
        false -> {false, json:decode(Text)}
    end.

mcp_test_() ->
    {setup, fun setup/0, fun(_) -> ok end,
     [
      {"initialize reports the protocol version and tools capability",
       fun() ->
               #{<<"result">> := R} = rpc(#{jsonrpc => <<"2.0">>, id => 1,
                                            method => <<"initialize">>, params => #{}}),
               ?assertEqual(<<"2025-06-18">>, maps:get(<<"protocolVersion">>, R)),
               ?assert(maps:is_key(<<"tools">>, maps:get(<<"capabilities">>, R)))
       end},
      {"notifications get no reply",
       fun() ->
               ?assertEqual(no_reply, bsm_mcp:handle_line(
                                        <<"{\"jsonrpc\":\"2.0\",\"method\":\"notifications/initialized\"}">>))
       end},
      {"tools/list advertises every query tool with a schema",
       fun() ->
               #{<<"result">> := #{<<"tools">> := Tools}} =
                   rpc(#{jsonrpc => <<"2.0">>, id => 2, method => <<"tools/list">>}),
               Names = lists:sort([maps:get(<<"name">>, T) || T <- Tools]),
               ?assertEqual([<<"find_teams">>, <<"head_to_head">>, <<"league_stats">>,
                             <<"search_matches">>, <<"search_players">>, <<"standings">>,
                             <<"team_record">>], Names),
               [?assertMatch(#{<<"type">> := <<"object">>}, maps:get(<<"inputSchema">>, T))
                || T <- Tools]
       end},
      {"search_matches returns structured JSON with a total",
       fun() ->
               {false, #{<<"total">> := Total, <<"matches">> := Ms}} =
                   call(<<"search_matches">>, #{<<"team">> => <<"Flamengo">>,
                                                <<"opponent">> => <<"Fluminense">>,
                                                <<"limit">> => 2}),
               ?assert(Total > 2),
               ?assertEqual(2, length(Ms))
       end},
      {"numeric arguments may be sent as strings",
       fun() ->
               {false, #{<<"matches">> := Ms}} =
                   call(<<"search_matches">>, #{<<"team">> => <<"Palmeiras">>,
                                                <<"season">> => <<"2019">>, <<"limit">> => 50}),
               ?assert(lists:all(fun(M) -> binary:part(maps:get(<<"date">>, M), 0, 4) =:= <<"2019">> end, Ms))
       end},
      {"standings returns the table as JSON",
       fun() ->
               {false, #{<<"table">> := [First | _]}} = call(<<"standings">>, #{<<"season">> => 2019}),
               ?assertMatch(#{<<"team">> := <<"Flamengo">>, <<"points">> := 90, <<"position">> := 1},
                            First)
       end},
      {"a bad argument is reported as a tool error, not a protocol error",
       fun() ->
               ?assertMatch({true, _}, call(<<"search_matches">>, #{<<"season">> => <<"abc">>}))
       end},
      {"a missing required argument is a tool error",
       fun() ->
               ?assertMatch({true, _}, call(<<"team_record">>, #{}))
       end},
      {"an unknown tool is a JSON-RPC error",
       fun() ->
               #{<<"error">> := #{<<"code">> := Code}} =
                   rpc(#{jsonrpc => <<"2.0">>, id => 3, method => <<"tools/call">>,
                         params => #{name => <<"nope">>, arguments => #{}}}),
               ?assertEqual(-32602, Code)
       end},
      {"malformed JSON gets a parse error with a null id",
       fun() ->
               #{<<"error">> := #{<<"code">> := Code}, <<"id">> := Id} =
                   json:decode(bsm_mcp:handle_line(<<"{not json">>)),
               ?assertEqual({-32700, null}, {Code, Id})
       end},
      {"an unknown method gets method-not-found",
       fun() ->
               #{<<"error">> := #{<<"code">> := Code}} =
                   rpc(#{jsonrpc => <<"2.0">>, id => 4, method => <<"resources/list">>}),
               ?assertEqual(-32601, Code)
       end}
     ]}.
