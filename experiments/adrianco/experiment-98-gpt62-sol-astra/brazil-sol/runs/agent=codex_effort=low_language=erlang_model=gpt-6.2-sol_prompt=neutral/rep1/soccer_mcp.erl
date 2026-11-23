-module(soccer_mcp).
-export([main/1, handle/2]).

-define(PROTOCOL, <<"2025-11-25">>).

main(Args) ->
    Directory = case Args of
        [Path] -> Path;
        [] -> filename:join([filename:dirname(escript:script_name()), "..", "data", "kaggle"])
    end,
    try soccer_data:load(Directory) of
        Data ->
            ok = io:setopts(standard_io, [binary, {encoding, unicode}]),
            loop(Data)
    catch
        error:Reason ->
            io:format(standard_error, "Soccer server failed: ~tp~n", [Reason]),
            halt(1)
    end.

loop(Data) ->
    case io:get_line(standard_io, "") of
        eof -> ok;
        {error, Reason} -> error({stdin, Reason});
        Line ->
            case handle(Line, Data) of
                none -> ok;
                Response -> io:put_chars(standard_io, [json:encode(Response), $\n])
            end,
            loop(Data)
    end.

handle(Line, Data) ->
    Decoded = try {ok, json:decode(Line)} catch error:_ -> parse_error end,
    case Decoded of
        parse_error -> failure(null, -32700, <<"Parse error">>);
        {ok, Message} -> dispatch(Message, Data)
    end.

dispatch(#{<<"jsonrpc">> := <<"2.0">>, <<"method">> := Method} = Request, Data)
  when is_binary(Method) ->
    case maps:find(<<"id">>, Request) of
        error -> none;
        {ok, Id} when is_integer(Id); is_binary(Id); Id =:= null ->
            Params = maps:get(<<"params">>, Request, #{}),
            call(Method, Id, Params, Data);
        _ -> failure(null, -32600, <<"Invalid request ID">>)
    end;
dispatch(_, _) -> failure(null, -32600, <<"Invalid request">>).

call(_, Id, Params, _) when not is_map(Params) ->
    failure(Id, -32602, <<"params must be an object">>);
call(<<"initialize">>, Id, Params, _) ->
    Requested = maps:get(<<"protocolVersion">>, Params, ?PROTOCOL),
    Versions = [?PROTOCOL, <<"2025-06-18">>, <<"2025-03-26">>, <<"2024-11-05">>],
    Version = case lists:member(Requested, Versions) of true -> Requested; false -> ?PROTOCOL end,
    result(Id, #{protocolVersion => Version, capabilities => #{tools => #{}},
                 serverInfo => #{name => <<"brazilian-soccer">>, version => <<"1.0.0">>},
                 instructions => <<"Use these tools to answer questions about the supplied Brazilian soccer datasets. Explain missing coverage when relevant and treat FIFA club memberships as a snapshot.">>});
call(<<"ping">>, Id, _, _) -> result(Id, #{});
call(<<"tools/list">>, Id, _, _) -> result(Id, #{tools => soccer_query:tools()});
call(<<"tools/call">>, Id, #{<<"name">> := Name} = Params, Data) when is_binary(Name) ->
    case lists:any(fun(#{name := N}) -> N =:= Name end, soccer_query:tools()) of
        false -> failure(Id, -32602, <<"Unknown tool">>);
        true ->
            case soccer_query:run(Name, maps:get(<<"arguments">>, Params, #{}), Data) of
                {ok, Output} -> result(Id, tool_result(Output));
                {error, Message} ->
                    result(Id, #{content => [#{type => <<"text">>, text => Message}], isError => true})
            end
    end;
call(<<"tools/call">>, Id, _, _) -> failure(Id, -32602, <<"A tool name is required">>);
call(_, Id, _, _) -> failure(Id, -32601, <<"Method not found">>).

tool_result(Output) ->
    #{content => [#{type => <<"text">>, text => iolist_to_binary(json:encode(Output))}],
      structuredContent => Output, isError => false}.

result(Id, Output) -> #{jsonrpc => <<"2.0">>, id => Id, result => Output}.
failure(Id, Code, Message) ->
    #{jsonrpc => <<"2.0">>, id => Id, error => #{code => Code, message => Message}}.
