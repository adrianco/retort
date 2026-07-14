-module(br_soccer_mcp_handler_tests).
-include_lib("eunit/include/eunit.hrl").

%% Sample in-memory dataset for handler tests (no file I/O)
sample_data() ->
    Matches = [
        #{<<"home_team">> => <<"Flamengo-RJ">>,
          <<"away_team">> => <<"Fluminense-RJ">>,
          <<"home_goal">> => <<"2">>,
          <<"away_goal">> => <<"1">>,
          <<"season">> => <<"2023">>,
          <<"datetime">> => <<"2023-04-15 18:00:00">>,
          competition => brasileirao},
        #{<<"home_team">> => <<"Palmeiras-SP">>,
          <<"away_team">> => <<"Flamengo-RJ">>,
          <<"home_goal">> => <<"0">>,
          <<"away_goal">> => <<"0">>,
          <<"season">> => <<"2023">>,
          <<"datetime">> => <<"2023-06-20 16:00:00">>,
          competition => brasileirao}
    ],
    Players = [
        #{<<"Name">> => <<"G. Barbosa">>,
          <<"Nationality">> => <<"Brazil">>,
          <<"Overall">> => <<"78">>,
          <<"Club">> => <<"Flamengo">>,
          <<"Position">> => <<"ST">>,
          <<"Age">> => <<"22">>}
    ],
    #{
        brasileirao  => Matches,
        copa_brasil  => [],
        libertadores => [],
        br_football  => [],
        historical   => [],
        players      => Players
    }.

%% TDD Cycle 1: Initialize request
handle_initialize_test() ->
    Req = #{<<"jsonrpc">> => <<"2.0">>,
            <<"id">> => 1,
            <<"method">> => <<"initialize">>,
            <<"params">> => #{<<"protocolVersion">> => <<"2024-11-05">>,
                              <<"capabilities">> => #{},
                              <<"clientInfo">> => #{<<"name">> => <<"test">>}}},
    {ok, Resp} = br_soccer_mcp_handler:handle(Req, sample_data()),
    ?assertEqual(<<"2.0">>, maps:get(<<"jsonrpc">>, Resp)),
    ?assertEqual(1, maps:get(<<"id">>, Resp)),
    Result = maps:get(<<"result">>, Resp),
    ?assert(maps:is_key(<<"serverInfo">>, Result)),
    ?assert(maps:is_key(<<"capabilities">>, Result)).

%% TDD Cycle 2: tools/list request
handle_tools_list_test() ->
    Req = #{<<"jsonrpc">> => <<"2.0">>,
            <<"id">> => 2,
            <<"method">> => <<"tools/list">>,
            <<"params">> => #{}},
    {ok, Resp} = br_soccer_mcp_handler:handle(Req, sample_data()),
    Result = maps:get(<<"result">>, Resp),
    Tools = maps:get(<<"tools">>, Result),
    ?assert(length(Tools) >= 5),
    Names = [maps:get(<<"name">>, T) || T <- Tools],
    ?assert(lists:member(<<"search_matches">>, Names)),
    ?assert(lists:member(<<"team_stats">>, Names)),
    ?assert(lists:member(<<"search_players">>, Names)),
    ?assert(lists:member(<<"head_to_head">>, Names)),
    ?assert(lists:member(<<"competition_standings">>, Names)).

%% TDD Cycle 3: tools/call search_matches
handle_search_matches_test() ->
    Req = #{<<"jsonrpc">> => <<"2.0">>,
            <<"id">> => 3,
            <<"method">> => <<"tools/call">>,
            <<"params">> => #{
                <<"name">> => <<"search_matches">>,
                <<"arguments">> => #{<<"team">> => <<"Flamengo">>}
            }},
    {ok, Resp} = br_soccer_mcp_handler:handle(Req, sample_data()),
    Result = maps:get(<<"result">>, Resp),
    Content = maps:get(<<"content">>, Result),
    ?assert(length(Content) > 0),
    Text = maps:get(<<"text">>, hd(Content)),
    ?assert(binary:match(Text, <<"Flamengo">>) =/= nomatch).

%% TDD Cycle 4: tools/call team_stats
handle_team_stats_test() ->
    Req = #{<<"jsonrpc">> => <<"2.0">>,
            <<"id">> => 4,
            <<"method">> => <<"tools/call">>,
            <<"params">> => #{
                <<"name">> => <<"team_stats">>,
                <<"arguments">> => #{<<"team">> => <<"Flamengo">>}
            }},
    {ok, Resp} = br_soccer_mcp_handler:handle(Req, sample_data()),
    Result = maps:get(<<"result">>, Resp),
    Content = maps:get(<<"content">>, Result),
    Text = maps:get(<<"text">>, hd(Content)),
    ?assert(binary:match(Text, <<"Flamengo">>) =/= nomatch),
    ?assert(binary:match(Text, <<"matches">>) =/= nomatch).

%% TDD Cycle 5: tools/call search_players
handle_search_players_test() ->
    Req = #{<<"jsonrpc">> => <<"2.0">>,
            <<"id">> => 5,
            <<"method">> => <<"tools/call">>,
            <<"params">> => #{
                <<"name">> => <<"search_players">>,
                <<"arguments">> => #{<<"nationality">> => <<"Brazil">>}
            }},
    {ok, Resp} = br_soccer_mcp_handler:handle(Req, sample_data()),
    Result = maps:get(<<"result">>, Resp),
    Content = maps:get(<<"content">>, Result),
    Text = maps:get(<<"text">>, hd(Content)),
    ?assert(binary:match(Text, <<"Barbosa">>) =/= nomatch).

%% TDD Cycle 6: tools/call head_to_head
handle_head_to_head_test() ->
    Req = #{<<"jsonrpc">> => <<"2.0">>,
            <<"id">> => 6,
            <<"method">> => <<"tools/call">>,
            <<"params">> => #{
                <<"name">> => <<"head_to_head">>,
                <<"arguments">> => #{<<"team1">> => <<"Flamengo">>,
                                     <<"team2">> => <<"Fluminense">>}
            }},
    {ok, Resp} = br_soccer_mcp_handler:handle(Req, sample_data()),
    Result = maps:get(<<"result">>, Resp),
    Content = maps:get(<<"content">>, Result),
    Text = maps:get(<<"text">>, hd(Content)),
    ?assert(byte_size(Text) > 0).

%% TDD Cycle 7: unknown method returns error
handle_unknown_method_test() ->
    Req = #{<<"jsonrpc">> => <<"2.0">>,
            <<"id">> => 7,
            <<"method">> => <<"unknown/method">>,
            <<"params">> => #{}},
    {ok, Resp} = br_soccer_mcp_handler:handle(Req, sample_data()),
    ?assert(maps:is_key(<<"error">>, Resp)).

%% TDD Cycle 8: JSON encode/decode round trip
json_roundtrip_test() ->
    Map = #{<<"key">> => <<"value">>, <<"num">> => 42},
    Encoded = br_soccer_mcp_handler:encode_json(Map),
    Decoded = br_soccer_mcp_handler:decode_json(Encoded),
    ?assertEqual(<<"value">>, maps:get(<<"key">>, Decoded)),
    ?assertEqual(42, maps:get(<<"num">>, Decoded)).
