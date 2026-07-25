%% JSON-RPC 2.0 message handling for the MCP protocol (transport-agnostic;
%% maps in, maps out). Implements initialize, ping, tools/list and tools/call.
-module(bsmcp_rpc).

-export([handle/1, parse_error_reply/0]).

-define(PROTOCOL_VERSION, <<"2025-06-18">>).
-define(SERVER_INFO,
        #{name => <<"brazilian-soccer-mcp">>,
          title => <<"Brazilian Soccer Knowledge Graph">>,
          version => <<"1.0.0">>}).

%% -> {reply, map()} | noreply
handle(Msg) when is_map(Msg) ->
    Method = maps:get(<<"method">>, Msg, undefined),
    Id = maps:get(<<"id">>, Msg, undefined),
    case {Method, Id} of
        {undefined, undefined} ->
            noreply;
        {undefined, _} ->
            %% A response from the client (has id but no method): ignore.
            noreply;
        {_, undefined} ->
            handle_notification(Method),
            noreply;
        _ ->
            handle_request(Method, maps:get(<<"params">>, Msg, #{}), Id)
    end;
handle(_) ->
    {reply, error_reply(null, -32600, <<"Invalid Request">>)}.

handle_notification(_Method) ->
    %% notifications/initialized, notifications/cancelled, ... nothing to do.
    ok.

handle_request(<<"initialize">>, Params, Id) ->
    Requested = case Params of
                    #{<<"protocolVersion">> := V} when is_binary(V) -> V;
                    _ -> ?PROTOCOL_VERSION
                end,
    Version = case lists:member(Requested, [<<"2024-11-05">>, <<"2025-03-26">>,
                                            <<"2025-06-18">>]) of
                  true -> Requested;
                  false -> ?PROTOCOL_VERSION
              end,
    {reply, result_reply(Id, #{protocolVersion => Version,
                               capabilities => #{tools => #{}},
                               serverInfo => ?SERVER_INFO})};

handle_request(<<"ping">>, _Params, Id) ->
    {reply, result_reply(Id, #{})};

handle_request(<<"tools/list">>, _Params, Id) ->
    {reply, result_reply(Id, #{tools => bsmcp_tools:tools()})};

handle_request(<<"tools/call">>, Params, Id) ->
    case Params of
        #{<<"name">> := Name} when is_binary(Name) ->
            Args = case maps:get(<<"arguments">>, Params, #{}) of
                       A when is_map(A) -> A;
                       _ -> #{}
                   end,
            case bsmcp_tools:call(Name, Args) of
                {ok, Text} ->
                    {reply, result_reply(Id, tool_result(Text, false))};
                {error, Text} ->
                    %% Tool-level failures are reported inside the result per
                    %% the MCP spec, so the LLM can see and react to them.
                    {reply, result_reply(Id, tool_result(Text, true))}
            end;
        _ ->
            {reply, error_reply(Id, -32602,
                                <<"Invalid params: missing tool name">>)}
    end;

handle_request(<<"resources/list">>, _Params, Id) ->
    {reply, result_reply(Id, #{resources => []})};

handle_request(<<"prompts/list">>, _Params, Id) ->
    {reply, result_reply(Id, #{prompts => []})};

handle_request(Method, _Params, Id) ->
    {reply, error_reply(Id, -32601,
                        iolist_to_binary([<<"Method not found: ">>, Method]))}.

tool_result(Text, IsError) ->
    #{content => [#{type => <<"text">>, text => Text}],
      isError => IsError}.

result_reply(Id, Result) ->
    #{jsonrpc => <<"2.0">>, id => Id, result => Result}.

error_reply(Id, Code, Message) ->
    #{jsonrpc => <<"2.0">>, id => Id,
      error => #{code => Code, message => Message}}.

parse_error_reply() ->
    error_reply(null, -32700, <<"Parse error">>).
