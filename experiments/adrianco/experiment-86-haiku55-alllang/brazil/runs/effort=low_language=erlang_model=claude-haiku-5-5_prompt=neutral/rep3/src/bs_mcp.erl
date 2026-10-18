%%% Model Context Protocol server over stdio (newline-delimited JSON-RPC 2.0).
%%%
%%% Supported methods: initialize, ping, tools/list, tools/call. Notifications
%%% (messages without an id) are accepted and never answered. stdout carries
%%% protocol messages only; diagnostics go to stderr.
-module(bs_mcp).

-export([run/1, handle_line/2]).

-define(PROTOCOL_VERSION, <<"2024-11-05">>).

%% Reads requests until end of input.
-spec run(map()) -> ok.
run(Data) ->
    case io:get_line(standard_io, "") of
        eof -> ok;
        {error, _} -> ok;
        Line ->
            case handle_line(unicode:characters_to_binary(Line), Data) of
                no_reply -> ok;
                Reply -> io:put_chars(standard_io, [Reply, $\n])
            end,
            run(Data)
    end.

%% Returns the encoded response as a UTF-8 binary, or no_reply.
-spec handle_line(binary(), map()) -> binary() | no_reply.
handle_line(Line, Data) ->
    case string:trim(Line) of
        <<>> -> no_reply;
        Trimmed ->
            try json:decode(Trimmed) of
                Msg when is_map(Msg) -> dispatch(Msg, Data);
                _ -> encode(error_reply(null, -32600, <<"Invalid Request">>))
            catch
                _:_ -> encode(error_reply(null, -32700, <<"Parse error">>))
            end
    end.

dispatch(Msg, Data) ->
    case maps:find(<<"id">>, Msg) of
        error -> no_reply;   % notification
        {ok, Id} ->
            Method = maps:get(<<"method">>, Msg, <<>>),
            Params = maps:get(<<"params">>, Msg, #{}),
            case handle(Method, Params, Data) of
                {result, R} -> encode(#{jsonrpc => <<"2.0">>, id => Id, result => R});
                {error, Code, Text} -> encode(error_reply(Id, Code, Text))
            end
    end.

handle(<<"initialize">>, _Params, _Data) ->
    {result, #{protocolVersion => ?PROTOCOL_VERSION,
               capabilities => #{tools => #{}},
               serverInfo => #{name => <<"brazilian-soccer-mcp">>, version => <<"0.1.0">>}}};
handle(<<"ping">>, _Params, _Data) ->
    {result, #{}};
handle(<<"tools/list">>, _Params, _Data) ->
    {result, #{tools => bs_tools:list()}};
handle(<<"tools/call">>, Params, Data) when is_map(Params) ->
    Name = maps:get(<<"name">>, Params, <<>>),
    Args = case maps:get(<<"arguments">>, Params, #{}) of
               A when is_map(A) -> A;
               _ -> #{}
           end,
    {result, tool_result(Name, Args, Data)};
handle(<<"tools/call">>, _Params, _Data) ->
    {error, -32602, <<"Invalid params">>};
handle(_Method, _Params, _Data) ->
    {error, -32601, <<"Method not found">>}.

%% Tool failures are returned as results with isError so the model can retry.
tool_result(Name, Args, Data) ->
    {Text, IsError} =
        try bs_tools:call(Name, Args, Data) of
            {ok, T} -> {T, false};
            {error, T} -> {T, true}
        catch
            Class:Reason:Stack ->
                io:format(standard_error, "tool ~ts failed: ~p:~p~n~p~n",
                          [Name, Class, Reason, Stack]),
                {<<"Internal error while running the tool.">>, true}
        end,
    #{content => [#{type => <<"text">>, text => Text}], isError => IsError}.

error_reply(Id, Code, Text) ->
    #{jsonrpc => <<"2.0">>, id => Id, error => #{code => Code, message => Text}}.

encode(Map) ->
    unicode:characters_to_binary(json:encode(Map)).
