-module(brazilian_soccer_mcp).
-behaviour(application).
-export([start/2, stop/1, run/0, handle/1, tools/0]).

start(_,_) -> soccer_data:load(), {ok,self()}.
stop(_) -> soccer_data:clear().
run() -> soccer_data:load(), loop().
loop() -> case io:get_line("") of eof -> ok; Line -> case soccer_json:decode(unicode:characters_to_binary(Line)) of {ok,Req}-> reply(handle(Req)); _->reply(error_response(null,-32700,<<"Parse error">>)) end, loop() end.
reply(M) -> io:format("~s~n", [soccer_json:encode(M)]).
handle(#{<<"method">> := <<"initialize">>} = R) -> result(id(R), #{<<"protocolVersion">>=><<"2024-11-05">>, <<"capabilities">>=>#{<<"tools">>=>#{}}, <<"serverInfo">>=>#{<<"name">>=><<"brazilian-soccer">>,<<"version">>=><<"0.1.0">>}});
handle(#{<<"method">> := <<"tools/list">>} = R) -> result(id(R), #{<<"tools">>=>tools()});
handle(#{<<"method">> := <<"tools/call">>, <<"params">> := P} = R) ->
    Name=maps:get(<<"name">>,P), Args=maps:get(<<"arguments">>,P,#{}),
    try result(id(R), #{<<"content">>=>[#{<<"type">>=><<"text">>,<<"text">>=>soccer_json:encode(call(Name,Args))}]}) catch _:E -> error_response(id(R),-32602,unicode:characters_to_binary(io_lib:format("~p",[E])) ) end;
handle(R) -> error_response(id(R),-32601,<<"Method not found">>).
id(R)->maps:get(<<"id">>,R,null). result(I,V)->#{<<"jsonrpc">>=><<"2.0">>,<<"id">>=>I,<<"result">>=>V}. error_response(I,C,M)->#{<<"jsonrpc">>=><<"2.0">>,<<"id">>=>I,<<"error">>=>#{<<"code">>=>C,<<"message">>=>M}}.
call(<<"search_matches">>,A)->soccer_query:find_matches(A); call(<<"team_stats">>,A)->soccer_query:team_stats(A); call(<<"head_to_head">>,A)->soccer_query:head_to_head(maps:get(<<"team_a">>,A),maps:get(<<"team_b">>,A)); call(<<"search_players">>,A)->soccer_query:find_players(A); call(<<"standings">>,A)->soccer_query:standings(maps:get(<<"competition">>,A,<<"Brasileirao">>),maps:get(<<"season">>,A)); call(<<"biggest_wins">>,A)->soccer_query:biggest_wins(A); call(_,_) -> error(unknown_tool).
tools() -> [tool(<<"search_matches">>,<<"Find matches by team, opponent, season, competition, dates, or round">>), tool(<<"team_stats">>,<<"Calculate a team's wins, draws, losses and goals">>), tool(<<"head_to_head">>,<<"Compare two teams">>), tool(<<"search_players">>,<<"Find FIFA players by name, nationality, club or position">>), tool(<<"standings">>,<<"Calculate a season table from results">>), tool(<<"biggest_wins">>,<<"Find largest score margins">>)].
tool(Name,Desc)->#{<<"name">>=>Name,<<"description">>=>Desc,<<"inputSchema">>=>#{<<"type">>=><<"object">>}}.
