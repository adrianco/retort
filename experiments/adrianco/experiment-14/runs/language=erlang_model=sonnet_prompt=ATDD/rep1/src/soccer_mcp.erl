%% Brazilian Soccer MCP Server - escript entry point and MCP protocol handler.
%% Reads newline-delimited JSON-RPC 2.0 messages from stdin, writes responses to stdout.
-module(soccer_mcp).
-export([main/1, handle_message/1]).

%%--------------------------------------------------------------------
%% Escript Entry Point
%%--------------------------------------------------------------------

main(_Args) ->
    ok = soccer_data:init(),
    loop(<<>>).

loop(Buffer) ->
    case io:get_line("") of
        eof -> ok;
        {error, _} -> ok;
        Line ->
            LineBin = unicode:characters_to_binary(Line, utf8),
            Trimmed = string:trim(LineBin),
            case Trimmed of
                <<>> -> loop(Buffer);
                _ ->
                    case handle_message(Trimmed) of
                        none -> ok;
                        Response ->
                            RespBin = iolist_to_binary(json:encode(Response)),
                            ok = file:write(standard_io, <<RespBin/binary, "\n">>)
                    end,
                    loop(<<>>)
            end
    end.

%%--------------------------------------------------------------------
%% MCP Protocol Handler (public for testing)
%%--------------------------------------------------------------------

handle_message(JsonBin) when is_binary(JsonBin) ->
    try
        Msg = json:decode(JsonBin),
        process_message(Msg)
    catch
        _:_ -> none
    end.

process_message(#{<<"jsonrpc">> := <<"2.0">>, <<"method">> := Method, <<"id">> := Id} = Msg) ->
    Params = maps:get(<<"params">>, Msg, #{}),
    case dispatch(Method, Params) of
        {ok, Result} ->
            #{<<"jsonrpc">> => <<"2.0">>, <<"id">> => Id, <<"result">> => Result};
        {error, Code, ErrMsg} ->
            #{<<"jsonrpc">> => <<"2.0">>, <<"id">> => Id,
              <<"error">> => #{<<"code">> => Code, <<"message">> => ErrMsg}}
    end;
process_message(#{<<"jsonrpc">> := <<"2.0">>, <<"method">> := _}) ->
    %% Notification - no id, no response
    none;
process_message(_) ->
    none.

%%--------------------------------------------------------------------
%% Method Dispatch
%%--------------------------------------------------------------------

dispatch(<<"initialize">>, _Params) ->
    {ok, #{
        <<"protocolVersion">> => <<"2024-11-05">>,
        <<"capabilities">>    => #{<<"tools">> => #{}},
        <<"serverInfo">>      => #{
            <<"name">>    => <<"brazilian-soccer-mcp">>,
            <<"version">> => <<"1.0.0">>
        }
    }};

dispatch(<<"tools/list">>, _Params) ->
    {ok, #{<<"tools">> => soccer_tools:list()}};

dispatch(<<"tools/call">>, Params) ->
    Name = maps:get(<<"name">>, Params, <<>>),
    Args = maps:get(<<"arguments">>, Params, #{}),
    case soccer_tools:call(Name, Args) of
        {ok, Text} ->
            {ok, #{
                <<"content">> => [#{<<"type">> => <<"text">>, <<"text">> => Text}]
            }};
        {error, ErrMsg} ->
            {ok, #{
                <<"content">>  => [#{<<"type">> => <<"text">>, <<"text">> => ErrMsg}],
                <<"isError">>  => true
            }}
    end;

dispatch(_, _) ->
    {error, -32601, <<"Method not found">>}.
