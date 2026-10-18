%% Context: MCP server over stdio speaking JSON-RPC 2.0, one message per line.
%% Implements initialize, ping, tools/list and tools/call. Logs go to stderr
%% only, because stdout carries the protocol. Uses OTP's built-in json module.
-module(soccer_mcp).
-export([main/1, handle/2]).

-define(PROTOCOL_VERSION, <<"2024-11-05">>).

main(_Args) ->
    Dir = os:getenv("SOCCER_DATA_DIR", "data/kaggle"),
    Data = soccer_loader:load(Dir),
    io:format(standard_error, "soccer_mcp: loaded ~B matches, ~B players from ~ts~n",
              [length(maps:get(matches, Data)), length(maps:get(players, Data)), Dir]),
    loop(Data).

loop(Data) ->
    case io:get_line(standard_io, "") of
        eof -> ok;
        {error, _} -> ok;
        Line ->
            case unicode:characters_to_binary(Line) of
                <<>> -> ok;
                Bin ->
                    case string:trim(Bin) of
                        <<>> -> ok;
                        Trimmed -> respond(Trimmed, Data)
                    end
            end,
            loop(Data)
    end.

respond(Raw, Data) ->
    Reply = try json:decode(Raw) of
                Msg when is_map(Msg) -> handle(Msg, Data);
                _ -> reply_error(null, -32600, <<"Invalid request">>)
            catch
                error:_ -> reply_error(null, -32700, <<"Parse error">>)
            end,
    case Reply of
        no_reply -> ok;
        _ -> io:put_chars(standard_io, [json:encode(Reply), $\n])
    end.

-spec handle(map(), map()) -> map() | no_reply.
handle(#{<<"method">> := <<"initialize">>, <<"id">> := Id}, _) ->
    result(Id, #{protocolVersion => ?PROTOCOL_VERSION,
                 capabilities => #{tools => #{}},
                 serverInfo => #{name => <<"brazilian-soccer">>, version => <<"0.1.0">>}});
handle(#{<<"method">> := <<"notifications/", _/binary>>}, _) ->
    no_reply;
handle(#{<<"method">> := <<"ping">>, <<"id">> := Id}, _) ->
    result(Id, #{});
handle(#{<<"method">> := <<"tools/list">>, <<"id">> := Id}, _) ->
    result(Id, #{tools => soccer_tools:definitions()});
handle(#{<<"method">> := <<"tools/call">>, <<"id">> := Id} = Msg, Data) ->
    Params = maps:get(<<"params">>, Msg, #{}),
    Name = maps:get(<<"name">>, Params, <<>>),
    Args = maps:get(<<"arguments">>, Params, #{}),
    case soccer_tools:call(Name, Args, Data) of
        {ok, Text} -> result(Id, content(Text, false));
        {error, Msg2} -> result(Id, content(Msg2, true))
    end;
handle(#{<<"method">> := M, <<"id">> := Id}, _) ->
    reply_error(Id, -32601, <<"Method not found: ", M/binary>>);
handle(#{<<"id">> := Id}, _) ->
    reply_error(Id, -32600, <<"Invalid request">>);
handle(_, _) ->
    no_reply.

result(Id, R) ->
    #{jsonrpc => <<"2.0">>, id => Id, result => R}.

reply_error(Id, Code, Msg) ->
    #{jsonrpc => <<"2.0">>, id => Id, error => #{code => Code, message => Msg}}.

content(Text, IsError) ->
    #{content => [#{type => <<"text">>, text => Text}], isError => IsError}.
