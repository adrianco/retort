-module(soccer_mcp).
-export([main/1, handle/2, tools/0]).

main(Args) ->
    DataDir = case Args of [D|_] -> D; [] -> "data/kaggle" end,
    Data = soccer_data:load(DataDir), loop(Data).
loop(Data) ->
    case io:get_line("") of eof -> ok; Line -> io:format("~s~n", [soccer_json:encode(handle(Line, Data))]), loop(Data) end.

tools() -> [
 #{name=>"search_matches", description=>"Find matches by team, opponent, competition, or season.", inputSchema=>#{type=>"object"}},
 #{name=>"team_statistics", description=>"Calculate a team's wins, draws, losses and goals.", inputSchema=>#{type=>"object"}},
 #{name=>"head_to_head", description=>"Compare two teams in all loaded match data.", inputSchema=>#{type=>"object"}},
 #{name=>"search_players", description=>"Find FIFA players by name, nationality, club, or position.", inputSchema=>#{type=>"object"}},
 #{name=>"standings", description=>"Calculate league standings from results.", inputSchema=>#{type=>"object"}},
 #{name=>"ask_soccer", description=>"Answer a simple natural-language Brazilian soccer question.", inputSchema=>#{type=>"object"}}].

handle(Line, Data) ->
    Id = json_id(Line), Method = json_string(Line,"method"),
    Result = case Method of
      "initialize" -> #{protocolVersion=>"2024-11-05", capabilities=>#{tools=>#{}}, serverInfo=>#{name=>"brazilian-soccer-mcp",version=>"0.1.0"}};
      "tools/list" -> #{tools=>tools()};
      "tools/call" -> tool_call(Line,Data);
      _ -> #{error=>#{code=>-32601,message=>"Method not found"}}
    end,
    case maps:is_key(error,Result) of true -> #{jsonrpc=>"2.0",id=>Id,error=>maps:get(error,Result)}; false -> #{jsonrpc=>"2.0",id=>Id,result=>Result} end.
tool_call(Line,Data) ->
    Name=json_string(Line,"name"), F=filters(Line), Output = case Name of
      "search_matches" -> soccer_query:matches(Data,F);
      "team_statistics" -> soccer_query:team_stats(Data,maps:get(team,F,""),F);
      "head_to_head" -> soccer_query:head_to_head(Data,maps:get(team,F,""),maps:get(opponent,F,""));
      "search_players" -> soccer_query:players(Data,F);
      "standings" -> soccer_query:standings(Data,maps:get(competition,F,brasileirao),maps:get(season,F,0));
      "ask_soccer" -> soccer_query:answer(Data,maps:get(question,F,""));
      _ -> #{error=>#{code=>-32602,message=>"Unknown tool"}}
    end,
    case Output of
        #{error := _} -> Output;
        _ -> #{content=>[#{type=>"text",text=>unicode:characters_to_list(soccer_json:encode(Output))}]}
    end.
filters(Line) ->
    lists:foldl(fun({K,Type},A) -> case json_string(Line,atom_to_list(K)) of undefined -> A; V -> maps:put(K,case Type of integer->soccer_data:to_int(V); competition->competition(V); _->V end,A) end end, #{}, [{team,string},{opponent,string},{name,string},{nationality,string},{club,string},{position,string},{question,string},{date_from,string},{date_to,string},{season,integer},{competition,competition}]).
competition("brasileirao")->brasileirao; competition("copa_do_brasil")->copa_do_brasil; competition("libertadores")->libertadores; competition("historical")->historical; competition("extended")->extended; competition(_)->brasileirao.
json_id(Line) -> case re:run(Line, "\\\"id\\\"\\s*:\\s*([0-9]+)", [{capture,[1],list}]) of {match,[S]}->soccer_data:to_int(S); _->null end.
json_string(Line, Key) ->
    Pattern = "\\\"" ++ Key ++ "\\\"\\s*:\\s*\\\"([^\\\"]*)\\\"",
    case re:run(Line,Pattern,[{capture,[1],list},unicode]) of {match,[V]}->V; nomatch->undefined end.
