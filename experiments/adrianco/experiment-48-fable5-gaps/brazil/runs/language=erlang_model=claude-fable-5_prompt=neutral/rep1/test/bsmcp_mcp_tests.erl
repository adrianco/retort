%% Protocol-level tests: JSON-RPC / MCP handshake, tool listing, tool calls
%% through the same code path the stdio transport uses, the 20+ sample
%% questions from the specification, and the query-performance criteria.
-module(bsmcp_mcp_tests).
-include_lib("eunit/include/eunit.hrl").

mcp_test_() ->
    {setup,
     fun() -> {ok, _} = bsmcp_data:ensure_loaded() end,
     fun(_) -> ok end,
     {timeout, 180,
      [{"initialize handshake", fun initialize/0},
       {"initialized notification gets no reply", fun notification/0},
       {"ping", fun ping/0},
       {"tools/list exposes all tools with schemas", fun tools_list/0},
       {"tools/call runs a search end to end", fun tools_call/0},
       {"tool errors are reported in-result (isError)", fun tool_error/0},
       {"unknown method -> -32601", fun unknown_method/0},
       {"invalid JSON -> parse error", fun parse_error/0},
       {"UTF-8 survives the full JSON round trip", fun utf8_roundtrip/0},
       {"20+ sample questions are answerable", fun sample_questions/0},
       {"simple lookups < 2s, aggregates < 5s", fun performance/0}]}}.

%% Drive a request through the exact stdio path (line in -> JSON line out).
rpc(Map) ->
    Line = iolist_to_binary(json:encode(Map)),
    case bsmcp_server:handle_line(Line) of
        noreply -> noreply;
        Reply -> json:decode(iolist_to_binary(Reply))
    end.

call_tool(Name, Args) ->
    R = rpc(#{jsonrpc => <<"2.0">>, id => 99, method => <<"tools/call">>,
              params => #{name => Name, arguments => Args}}),
    #{<<"result">> := Result} = R,
    #{<<"content">> := [#{<<"type">> := <<"text">>, <<"text">> := Text}]} = Result,
    {maps:get(<<"isError">>, Result, false), Text}.

initialize() ->
    R = rpc(#{jsonrpc => <<"2.0">>, id => 0, method => <<"initialize">>,
              params => #{protocolVersion => <<"2025-06-18">>,
                          capabilities => #{},
                          clientInfo => #{name => <<"test">>, version => <<"0">>}}}),
    #{<<"jsonrpc">> := <<"2.0">>, <<"id">> := 0, <<"result">> := Res} = R,
    ?assertEqual(<<"2025-06-18">>, maps:get(<<"protocolVersion">>, Res)),
    ?assertMatch(#{<<"tools">> := _}, maps:get(<<"capabilities">>, Res)),
    ?assertMatch(#{<<"name">> := _}, maps:get(<<"serverInfo">>, Res)).

notification() ->
    ?assertEqual(noreply,
                 rpc(#{jsonrpc => <<"2.0">>,
                       method => <<"notifications/initialized">>})).

ping() ->
    ?assertMatch(#{<<"result">> := #{}},
                 rpc(#{jsonrpc => <<"2.0">>, id => 1, method => <<"ping">>})).

tools_list() ->
    #{<<"result">> := #{<<"tools">> := Tools}} =
        rpc(#{jsonrpc => <<"2.0">>, id => 2, method => <<"tools/list">>}),
    Names = [maps:get(<<"name">>, T) || T <- Tools],
    Expected = [<<"search_matches">>, <<"team_stats">>, <<"head_to_head">>,
                <<"competition_standings">>, <<"search_players">>,
                <<"league_stats">>, <<"biggest_wins">>, <<"data_summary">>],
    [?assert(lists:member(N, Names)) || N <- Expected],
    lists:foreach(
      fun(T) ->
              ?assert(is_binary(maps:get(<<"description">>, T))),
              ?assertMatch(#{<<"type">> := <<"object">>},
                           maps:get(<<"inputSchema">>, T))
      end, Tools).

tools_call() ->
    {IsError, Text} = call_tool(<<"search_matches">>,
                                #{team => <<"Flamengo">>,
                                  opponent => <<"Fluminense">>,
                                  limit => 5}),
    ?assertNot(IsError),
    ?assertMatch({_, _}, binary:match(Text, <<"Head-to-head">>)),
    ?assertMatch({_, _}, binary:match(Text, <<"Flamengo">>)).

tool_error() ->
    {IsError, Text} = call_tool(<<"search_matches">>,
                                #{team => <<"Real Madrid CF Espana">>}),
    ?assert(IsError),
    ?assertMatch({_, _}, binary:match(Text, <<"not found">>)),
    {IsError2, _} = call_tool(<<"no_such_tool">>, #{}),
    ?assert(IsError2).

unknown_method() ->
    #{<<"error">> := #{<<"code">> := Code}} =
        rpc(#{jsonrpc => <<"2.0">>, id => 3, method => <<"bogus/method">>}),
    ?assertEqual(-32601, Code).

parse_error() ->
    Reply = bsmcp_server:handle_line(<<"this is not json">>),
    #{<<"error">> := #{<<"code">> := Code}} =
        json:decode(iolist_to_binary(Reply)),
    ?assertEqual(-32700, Code),
    ?assertEqual(noreply, bsmcp_server:handle_line(<<"   \n">>)).

utf8_roundtrip() ->
    {false, Text} = call_tool(<<"search_matches">>,
                              #{team => <<"São Paulo"/utf8>>,
                                competition => <<"brasileirão"/utf8>>,
                                season => 2019, limit => 3}),
    %% valid UTF-8 out, with accented team names preserved
    ?assert(is_list(unicode:characters_to_list(Text))),
    ?assertMatch({_, _}, binary:match(Text, <<"match(es) found">>)).

%% "At least 20 sample questions can be answered" — each entry maps a natural
%% language question from the spec to a tool call that answers it.
sample_questions() ->
    Questions =
        [%% Match queries
         {"Show me all Flamengo vs Fluminense matches",
          <<"search_matches">>, #{team => <<"Flamengo">>, opponent => <<"Fluminense">>}},
         {"What matches did Palmeiras play in 2023?",
          <<"search_matches">>, #{team => <<"Palmeiras">>, season => 2023}},
         {"Find all Copa do Brasil finals",
          <<"search_matches">>, #{competition => <<"Copa do Brasil">>, stage => <<"final">>}},
         {"When did Flamengo last play Corinthians?",
          <<"search_matches">>, #{team => <<"Flamengo">>, opponent => <<"Corinthians">>, limit => 1}},
         {"Show me Flamengo matches from mid 2019",
          <<"search_matches">>, #{team => <<"Flamengo">>, date_from => <<"2019-06-01">>, date_to => <<"2019-08-31">>}},
         {"Show the 2018 Copa Libertadores knockout results",
          <<"search_matches">>, #{competition => <<"Libertadores">>, season => 2018, stage => <<"semifinals">>}},
         %% Team queries
         {"What is Corinthians' home record in 2022?",
          <<"team_stats">>, #{team => <<"Corinthians">>, season => 2022, venue => <<"home">>}},
         {"How did Santos do in the Copa do Brasil?",
          <<"team_stats">>, #{team => <<"Santos">>, competition => <<"Copa do Brasil">>}},
         {"Compare Palmeiras and Santos head-to-head",
          <<"head_to_head">>, #{team1 => <<"Palmeiras">>, team2 => <<"Santos">>}},
         {"Gremio vs Internacional derby record",
          <<"head_to_head">>, #{team1 => <<"Gremio">>, team2 => <<"Internacional">>}},
         {"What competitions has Palmeiras played in?",
          <<"team_stats">>, #{team => <<"Palmeiras">>}},
         %% Player queries
         {"Who is Neymar?",
          <<"search_players">>, #{name => <<"Neymar">>}},
         {"Find all Brazilian players in the dataset",
          <<"search_players">>, #{nationality => <<"Brazil">>}},
         {"Who are the highest-rated players at FC Barcelona?",
          <<"search_players">>, #{club => <<"Barcelona">>}},
         {"Show me the best Brazilian goalkeepers",
          <<"search_players">>, #{nationality => <<"Brazil">>, position => <<"goalkeeper">>}},
         {"Top Brazilian forwards rated 85+",
          <<"search_players">>, #{nationality => <<"Brazil">>, position => <<"forward">>, min_overall => 85}},
         %% Competition queries
         {"Who won the 2019 Brasileirão?",
          <<"competition_standings">>, #{season => 2019}},
         {"Which teams were relegated in 2018?",
          <<"competition_standings">>, #{season => 2018, limit => 20}},
         {"Show the 2013 Serie A table",
          <<"competition_standings">>, #{competition => <<"Serie A">>, season => 2013}},
         %% Statistical analysis
         {"What's the average goals per match in the Brasileirão?",
          <<"league_stats">>, #{competition => <<"brasileirao">>}},
         {"How did home advantage look in 2020?",
          <<"league_stats">>, #{competition => <<"brasileirao">>, season => 2020}},
         {"Show me the biggest wins in the dataset",
          <<"biggest_wins">>, #{}},
         {"Biggest Libertadores wins?",
          <<"biggest_wins">>, #{competition => <<"Libertadores">>}},
         {"What data do you have?",
          <<"data_summary">>, #{}}],
    ?assert(length(Questions) >= 20),
    lists:foreach(
      fun({Q, Tool, Args}) ->
              {IsError, Text} = call_tool(Tool, Args),
              ?assertEqual({Q, false}, {Q, IsError}),
              ?assert(byte_size(Text) > 10)
      end, Questions).

performance() ->
    {T1, _} = timer:tc(fun() ->
                               call_tool(<<"search_matches">>,
                                         #{team => <<"Flamengo">>,
                                           opponent => <<"Corinthians">>})
                       end),
    ?assert(T1 < 2_000_000),
    {T2, _} = timer:tc(fun() ->
                               call_tool(<<"competition_standings">>,
                                         #{season => 2019})
                       end),
    ?assert(T2 < 5_000_000),
    {T3, _} = timer:tc(fun() ->
                               call_tool(<<"league_stats">>, #{})
                       end),
    ?assert(T3 < 5_000_000).
