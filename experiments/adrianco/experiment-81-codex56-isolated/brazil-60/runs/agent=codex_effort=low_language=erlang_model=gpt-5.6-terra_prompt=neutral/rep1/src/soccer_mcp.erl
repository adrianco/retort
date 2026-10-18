-module(soccer_mcp).
-export([main/0, run/0, handle/2, tools/0]).
main() -> case soccer_data:load() of {ok,D}->loop(D);{error,E}->io:format(standard_error,"load failure ~p~n",[E]),halt(1) end.
run() -> main().
loop(D)->case io:get_line("") of eof->ok;L->case soccer_json:decode(iolist_to_binary(L)) of {ok,R}->reply(handle(R,D));{error,E}->reply(error_response(null,-32700,E)) end,loop(D) end.
reply(R)->io:format("~s~n",[soccer_json:encode(R)]).
handle(R,D)->Id=maps:get(<<"id">>,R,null),Method=maps:get(<<"method">>,R,<<>>),P=maps:get(<<"params">>,R,#{}),try case Method of
 <<"initialize">>->ok_response(Id,#{<<"protocolVersion">>=><<"2024-11-05">>,<<"serverInfo">>=>#{<<"name">>=><<"brazilian-soccer">>,<<"version">>=><<"0.1.0">>},<<"capabilities">>=>#{<<"tools">>=>#{}}});
 <<"tools/list">>->ok_response(Id,#{<<"tools">>=>tools()});
 <<"tools/call">>->X=call(maps:get(<<"name">>,P),maps:get(<<"arguments">>,P,#{}),D),ok_response(Id,#{<<"content">>=>[#{<<"type">>=><<"text">>,<<"text">>=>soccer_json:encode(X)}]});
 _->error_response(Id,-32601,<<"Method not found">>) end catch C:E->error_response(Id,-32602,unicode:characters_to_binary(io_lib:format("~p:~p",[C,E]))) end.
ok_response(Id,X)->#{<<"jsonrpc">>=><<"2.0">>,<<"id">>=>Id,<<"result">>=>X}.
call(<<"search_matches">>,A,D)->soccer_query:find_matches(D,keys(A));call(<<"team_stats">>,A,D)->soccer_query:team_stats(D,keys(A));call(<<"head_to_head">>,A,D)->soccer_query:head_to_head(D,maps:get(<<"team_a">>,A),maps:get(<<"team_b">>,A));call(<<"standings">>,A,D)->soccer_query:standings(D,maps:get(<<"competition">>,A,<<"Brasileirao">>),maps:get(<<"season">>,A));call(<<"search_players">>,A,D)->soccer_query:search_players(D,keys(A));call(<<"aggregate_stats">>,A,D)->soccer_query:aggregate(D,keys(A));call(<<"ask">>,A,D)->soccer_query:answer(D,maps:get(<<"question">>,A));call(_,_,_)->#{error=><<"Unknown tool">>}.
keys(M)->maps:from_list([{key(K),V}||{K,V}<-maps:to_list(M)]).
key(<<"team">>)->team;key(<<"home_team">>)->home_team;key(<<"away_team">>)->away_team;key(<<"season">>)->season;key(<<"competition">>)->competition;key(<<"from">>)->from;key(<<"to">>)->to;key(<<"limit">>)->limit;key(<<"venue">>)->venue;key(<<"name">>)->name;key(<<"nationality">>)->nationality;key(<<"club">>)->club;key(<<"position">>)->position.
error_response(Id,C,M)->#{<<"jsonrpc">>=><<"2.0">>,<<"id">>=>Id,<<"error">>=>#{<<"code">>=>C,<<"message">>=>M}}.
tools()->[tool(<<"search_matches">>,<<"Find matches by team, season, competition, date range, or home/away team">>, [<<"team">>, <<"home_team">>, <<"away_team">>, <<"season">>, <<"competition">>, <<"from">>, <<"to">>, <<"limit">>]),
          tool(<<"team_stats">>,<<"Wins, draws, losses and goals for a team">>, [<<"team">>, <<"season">>, <<"competition">>, <<"venue">>]),
          tool(<<"head_to_head">>,<<"Compare two teams">>, [<<"team_a">>, <<"team_b">>]),
          tool(<<"standings">>,<<"Calculate standings for a competition season">>, [<<"competition">>, <<"season">>]),
          tool(<<"search_players">>,<<"Search FIFA players by name, nationality, club or position">>, [<<"name">>, <<"nationality">>, <<"club">>, <<"position">>, <<"limit">>]),
          tool(<<"aggregate_stats">>,<<"Goals and home-win aggregates">>, [<<"season">>, <<"competition">>, <<"from">>, <<"to">>]),
          tool(<<"ask">>,<<"Small natural-language convenience query">>, [<<"question">>])].
tool(N,D, Names)->#{<<"name">>=>N,<<"description">>=>D,<<"inputSchema">>=>#{<<"type">>=><<"object">>, <<"properties">>=>maps:from_list([{Name, #{<<"type">>=><<"string">>}} || Name <- Names])}}.
