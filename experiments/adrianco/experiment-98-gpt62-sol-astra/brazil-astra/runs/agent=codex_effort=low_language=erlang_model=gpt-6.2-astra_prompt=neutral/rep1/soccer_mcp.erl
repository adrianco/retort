-module(soccer_mcp).
-export([main/0,handle/2]).

main() ->
    Dir=filename:join(filename:dirname(code:which(?MODULE)),"data/kaggle"),
    DB=soccer_data:load(Dir),
    io:setopts(standard_io,[binary,{encoding,latin1}]),
    loop(DB).
loop(DB) ->
    case file:read_line(standard_io) of
        eof -> ok;
        {ok,Line} ->
            Reply=try json:decode(Line) of R -> handle(R,DB)
                  catch error:_ -> failure(null,-32700,<<"Parse error">>) end,
            case Reply of
                silent -> ok;
                _ -> file:write(standard_io,[json:encode(Reply),$\n])
            end,
            loop(DB)
    end.

handle(#{<<"jsonrpc">>:= <<"2.0">>,<<"method">>:=Method}=Request,DB) when is_binary(Method) ->
    case maps:find(<<"id">>,Request) of
        error -> silent;
        {ok,Id} ->
            try dispatch(Method,maps:get(<<"params">>,Request,#{}),DB) of
                unknown -> failure(Id,-32601,<<"Method not found">>);
                Result -> #{jsonrpc=><<"2.0">>,id=>Id,result=>Result}
            catch error:_ -> failure(Id,-32602,<<"Invalid parameters">>) end
    end;
handle(_,_) -> failure(null,-32600,<<"Invalid request">>).
failure(Id,Code,Message) -> #{jsonrpc=><<"2.0">>,id=>Id,error=>#{code=>Code,message=>Message}}.
dispatch(<<"initialize">>,P,_) ->
    Versions=[<<"2025-11-25">>,<<"2025-06-18">>,<<"2025-03-26">>,<<"2024-11-05">>],
    Asked=maps:get(<<"protocolVersion">>,P,undefined),
    Version=case lists:member(Asked,Versions) of true -> Asked; false -> hd(Versions) end,
    #{protocolVersion=>Version,capabilities=>#{tools=>#{}},
      serverInfo=>#{name=><<"brazilian-soccer">>,version=><<"1.0">>},
      instructions=><<"Use tools for dataset questions. Paginate with offset and limit. Standings are computed from available scores. Check fixture coverage before claiming final positions. FIFA players are a separate historical snapshot.">>};
dispatch(<<"ping">>,_,_) -> #{};
dispatch(<<"tools/list">>,_,_) -> #{tools=>soccer_query:tools()};
dispatch(<<"tools/call">>,#{<<"name">>:=Name}=P,DB) ->
    Result=soccer_query:run(Name,maps:get(<<"arguments">>,P,#{}),DB),
    #{content=>[#{type=>text,text=>iolist_to_binary(json:encode(Result))}]};
dispatch(<<"tools/call">>,_,_) -> error(badarg);
dispatch(_,_,_) -> unknown.
