-module(bsmcp_server_tests).
-include_lib("eunit/include/eunit.hrl").

store() ->
    #{matches => [], players => []}.

process_line_returns_response_test() ->
    Line = bsmcp_mcp:encode(#{<<"jsonrpc">> => <<"2.0">>, <<"id">> => 1,
                              <<"method">> => <<"ping">>, <<"params">> => #{}}),
    {ok, Out} = bsmcp_server:process_line(Line, store()),
    Decoded = bsmcp_mcp:decode(Out),
    ?assertEqual(1, maps:get(<<"id">>, Decoded)),
    ?assertEqual(#{}, maps:get(<<"result">>, Decoded)).

process_line_notification_returns_none_test() ->
    Line = bsmcp_mcp:encode(#{<<"jsonrpc">> => <<"2.0">>,
                              <<"method">> => <<"notifications/initialized">>}),
    ?assertEqual(none, bsmcp_server:process_line(Line, store())).

process_line_blank_returns_none_test() ->
    ?assertEqual(none, bsmcp_server:process_line(<<"   ">>, store())).

process_line_invalid_json_returns_parse_error_test() ->
    {ok, Out} = bsmcp_server:process_line(<<"{not json">>, store()),
    Decoded = bsmcp_mcp:decode(Out),
    Error = maps:get(<<"error">>, Decoded),
    ?assertEqual(-32700, maps:get(<<"code">>, Error)).

load_store_from_data_dir_test() ->
    %% Integration: the real datasets load and are queryable.
    Store = bsmcp_server:load_store("data/kaggle"),
    ?assert(length(maps:get(matches, Store)) > 1000),
    ?assert(length(maps:get(players, Store)) > 1000).
