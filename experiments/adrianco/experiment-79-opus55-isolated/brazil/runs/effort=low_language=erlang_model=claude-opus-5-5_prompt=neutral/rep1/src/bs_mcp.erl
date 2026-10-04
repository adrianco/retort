%% Model Context Protocol (JSON-RPC 2.0) message handling.
%% Transport independent: handle_line/1 maps one JSON message to a reply.
-module(bs_mcp).
-export([handle_line/1, handle/1]).

-define(PROTOCOL, <<"2024-11-05">>).
-define(SUPPORTED, [<<"2024-11-05">>, <<"2025-03-26">>, <<"2025-06-18">>]).

-spec handle_line(binary()) -> {reply, binary()} | noreply.
handle_line(Line) ->
    case string:trim(Line) of
        <<>> -> noreply;
        Json ->
            Decoded = try {ok, json:decode(Json)} catch _:_ -> error end,
            Res = case Decoded of
                      {ok, Msgs} when is_list(Msgs), Msgs =/= [] ->
                          case [R || M <- Msgs, {reply, R} <- [handle(M)]] of
                              [] -> noreply;
                              Rs -> {reply, Rs}
                          end;
                      {ok, Msg} -> handle(Msg);
                      error -> {reply, rpc_error(null, -32700, <<"Parse error">>)}
                  end,
            case Res of
                noreply -> noreply;
                {reply, R} -> {reply, iolist_to_binary(json:encode(R))}
            end
    end.

%% One decoded message -> {reply, Map} | noreply
handle(#{<<"method">> := Method} = Msg) when is_binary(Method) ->
    Params = maps:get(<<"params">>, Msg, #{}),
    case maps:find(<<"id">>, Msg) of
        error -> noreply;                       % notification
        {ok, Id} ->
            try method(Method, Params) of
                {ok, Result} -> {reply, #{jsonrpc => <<"2.0">>, id => Id, result => Result}};
                {error, Code, Text} -> {reply, rpc_error(Id, Code, Text)}
            catch
                Class:Reason:Stack ->
                    logger:error("request failed: ~p:~p ~p", [Class, Reason, Stack]),
                    {reply, rpc_error(Id, -32603, <<"Internal error">>)}
            end
    end;
handle(#{<<"id">> := _, <<"result">> := _}) -> noreply;   % response to us: ignore
handle(#{<<"id">> := _, <<"error">> := _}) -> noreply;
handle(_) -> {reply, rpc_error(null, -32600, <<"Invalid Request">>)}.

method(<<"initialize">>, Params) ->
    Requested = case Params of
                    #{<<"protocolVersion">> := V} -> V;
                    _ -> ?PROTOCOL
                end,
    Version = case lists:member(Requested, ?SUPPORTED) of
                  true -> Requested;
                  false -> ?PROTOCOL
              end,
    {ok, #{protocolVersion => Version,
           capabilities => #{tools => #{listChanged => false}},
           serverInfo => #{name => <<"brazilian-soccer-mcp">>, version => <<"1.0.0">>},
           instructions => <<"Brazilian soccer knowledge base: Brasileirão, Copa do Brasil and "
                             "Libertadores matches plus FIFA player data. Team names may be given "
                             "in any common spelling."/utf8>>}};
method(<<"ping">>, _) -> {ok, #{}};
method(<<"tools/list">>, _) -> {ok, #{tools => bs_tools:list()}};
method(<<"tools/call">>, #{<<"name">> := Name} = Params) when is_binary(Name) ->
    Args = case maps:get(<<"arguments">>, Params, #{}) of
               null -> #{};
               A -> A
           end,
    case bs_tools:call(Name, Args) of
        {ok, Text} -> {ok, tool_result(Text, false)};
        {error, unknown_tool} -> {error, -32602, <<"Unknown tool: ", Name/binary>>};
        {error, Text} -> {ok, tool_result(Text, true)}
    end;
method(<<"tools/call">>, _) -> {error, -32602, <<"Invalid params: tool name is required">>};
method(<<"resources/list">>, _) -> {ok, #{resources => []}};
method(<<"prompts/list">>, _) -> {ok, #{prompts => []}};
method(Other, _) -> {error, -32601, <<"Method not found: ", Other/binary>>}.

tool_result(Text, IsError) ->
    #{content => [#{type => <<"text">>, text => Text}], isError => IsError}.

rpc_error(Id, Code, Text) ->
    #{jsonrpc => <<"2.0">>, id => Id, error => #{code => Code, message => Text}}.
