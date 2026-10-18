%% @doc Minimal MCP server over stdio: newline-delimited JSON-RPC 2.0.
%% stdout carries protocol messages only; diagnostics go to stderr.
-module(bsm_mcp).
-export([run/0, handle_line/1]).

-define(PROTOCOL_VERSION, <<"2025-06-18">>).
-define(SERVER_VERSION, <<"0.1.0">>).

-spec run() -> ok.
run() ->
    case file:read_line(standard_io) of
        {ok, Line} ->
            case handle_line(Line) of
                no_reply -> ok;
                %% put_chars takes UTF-8 binaries as text; file:write would treat them as latin1.
                Reply -> io:put_chars(standard_io, [Reply, $\n])
            end,
            run();
        eof -> ok;
        {error, _} -> ok
    end.

%% @doc One request line in, one encoded response out (or no_reply for
%% notifications and blank lines).
-spec handle_line(binary()) -> binary() | no_reply.
handle_line(Line) ->
    case bsm_text:trim(Line) of
        <<>> -> no_reply;
        Trimmed ->
            try json:decode(Trimmed) of
                Msg when is_map(Msg) -> dispatch(Msg);
                _ -> error_reply(null, -32600, <<"Invalid Request">>)
            catch error:_ -> error_reply(null, -32700, <<"Parse error">>)
            end
    end.

dispatch(#{<<"method">> := Method} = Msg) ->
    case maps:find(<<"id">>, Msg) of
        error -> no_reply;                                  % notification
        {ok, Id} -> request(Id, Method, maps:get(<<"params">>, Msg, #{}))
    end;
dispatch(Msg) when is_map(Msg) ->
    error_reply(maps:get(<<"id">>, Msg, null), -32600, <<"Invalid Request">>).

request(Id, <<"initialize">>, _) ->
    result(Id, #{protocolVersion => ?PROTOCOL_VERSION,
                 capabilities => #{tools => #{}},
                 serverInfo => #{name => <<"brazilian-soccer-mcp">>,
                                 version => ?SERVER_VERSION}});
request(Id, <<"ping">>, _) ->
    result(Id, #{});
request(Id, <<"tools/list">>, _) ->
    result(Id, #{tools => bsm_tools:definitions()});
request(Id, <<"tools/call">>, Params) when is_map(Params) ->
    Args = case maps:get(<<"arguments">>, Params, #{}) of
               M when is_map(M) -> M;
               _ -> #{}
           end,
    case bsm_tools:call(maps:get(<<"name">>, Params, <<>>), Args) of
        {ok, Text} ->
            result(Id, #{content => [#{type => <<"text">>, text => Text}], isError => false});
        {error, unknown_tool} ->
            error_reply(Id, -32602, <<"Unknown tool">>);
        {error, Msg} ->
            result(Id, #{content => [#{type => <<"text">>, text => Msg}], isError => true})
    end;
request(Id, _, _) ->
    error_reply(Id, -32601, <<"Method not found">>).

result(Id, Result) ->
    encode(#{jsonrpc => <<"2.0">>, id => Id, result => Result}).

error_reply(Id, Code, Msg) ->
    encode(#{jsonrpc => <<"2.0">>, id => Id, error => #{code => Code, message => Msg}}).

encode(Term) -> iolist_to_binary(json:encode(Term)).
