%%% MCP (Model Context Protocol) server: JSON-RPC 2.0 over stdio, one JSON
%%% message per line.  handle/1 is pure (decoded request -> reply) so it can
%%% be tested without a transport.
-module(brsoccer_mcp).
-export([main/1, start/0, serve/0, handle_line/1, handle/1]).

-define(PROTOCOL, <<"2024-11-05">>).
-define(SUPPORTED, [<<"2024-11-05">>, <<"2025-03-26">>, <<"2025-06-18">>]).

%% escript entry point
main(_Args) -> start().

start() ->
    %% stdout carries the protocol: keep logging on stderr only.
    _ = logger:remove_handler(default),
    ok = io:setopts(standard_io, [binary, {encoding, unicode}]),
    %% Load data eagerly so the first tool call is fast.
    case brsoccer_data:ensure_loaded() of
        ok -> ok;
        {error, E} -> io:format(standard_error, "brsoccer: data not loaded: ~p~n", [E])
    end,
    serve(),
    erlang:halt(0).

serve() ->
    case io:get_line(standard_io, "") of
        eof -> ok;
        {error, _} -> ok;
        Line ->
            case handle_line(Line) of
                noreply -> ok;
                {reply, Json} -> io:put_chars(standard_io, [Json, $\n])
            end,
            serve()
    end.

%% One raw line in -> noreply | {reply, JsonBinary}
-spec handle_line(binary() | string()) -> noreply | {reply, binary()}.
handle_line(Line0) ->
    Line = string:trim(unicode:characters_to_binary(Line0)),
    case Line of
        <<>> -> noreply;
        _ ->
            Decoded = try {ok, json:decode(Line)} catch _:_ -> error end,
            Reply = case Decoded of
                        error -> error_reply(null, -32700, <<"Parse error">>);
                        {ok, Batch} when is_list(Batch), Batch =/= [] ->
                            case [R || M <- Batch, R <- [handle(M)], R =/= noreply] of
                                [] -> noreply;
                                Rs -> Rs
                            end;
                        {ok, Msg} -> handle(Msg)
                    end,
            case Reply of
                noreply -> noreply;
                _ -> {reply, iolist_to_binary(json:encode(Reply))}
            end
    end.

%% Decoded JSON-RPC message -> reply map | noreply
-spec handle(term()) -> map() | noreply.
handle(#{<<"method">> := Method} = Msg) when is_binary(Method) ->
    Params = maps:get(<<"params">>, Msg, #{}),
    case maps:find(<<"id">>, Msg) of
        error -> noreply;                                   % notification
        {ok, Id} ->
            try method(Method, Params) of
                {ok, Result} -> #{jsonrpc => <<"2.0">>, id => Id, result => Result};
                {error, Code, Text} -> error_reply(Id, Code, Text)
            catch
                Class:Reason:Stack ->
                    io:format(standard_error, "brsoccer: ~p:~p~n~p~n", [Class, Reason, Stack]),
                    error_reply(Id, -32603, <<"Internal error">>)
            end
    end;
handle(#{<<"id">> := _} = Msg) when is_map_key(<<"result">>, Msg); is_map_key(<<"error">>, Msg) ->
    noreply;                                                % response to us: ignore
handle(_) ->
    error_reply(null, -32600, <<"Invalid Request">>).

method(<<"initialize">>, Params) ->
    Version = case Params of
                  #{<<"protocolVersion">> := V} ->
                      case lists:member(V, ?SUPPORTED) of true -> V; false -> ?PROTOCOL end;
                  _ -> ?PROTOCOL
              end,
    {ok, #{protocolVersion => Version,
           capabilities => #{tools => #{listChanged => false}},
           serverInfo => #{name => <<"brazilian-soccer-mcp">>, version => <<"1.0.0">>},
           instructions => <<"Query Brazilian soccer data (Brasileirão, Copa do Brasil, "
                             "Libertadores matches 2003-2023 and FIFA player ratings). "
                             "Team names are normalised; accents are optional."/utf8>>}};
method(<<"ping">>, _) -> {ok, #{}};
method(<<"tools/list">>, _) -> {ok, #{tools => brsoccer_tools:list()}};
method(<<"tools/call">>, #{<<"name">> := Name} = Params) when is_binary(Name) ->
    Args = case maps:get(<<"arguments">>, Params, #{}) of
               null -> #{};
               A -> A
           end,
    case lists:any(fun(#{name := N}) -> N =:= Name end, brsoccer_tools:list()) of
        false -> {error, -32602, <<"Unknown tool: ", Name/binary>>};
        true ->
            {IsError, Text} = case brsoccer_tools:call(Name, Args) of
                                  {ok, T} -> {false, T};
                                  {error, T} -> {true, T}
                              end,
            {ok, #{content => [#{type => <<"text">>, text => Text}], isError => IsError}}
    end;
method(<<"tools/call">>, _) -> {error, -32602, <<"Invalid params: tool name required">>};
method(<<"resources/list">>, _) -> {ok, #{resources => []}};
method(<<"prompts/list">>, _) -> {ok, #{prompts => []}};
method(_, _) -> {error, -32601, <<"Method not found">>}.

error_reply(Id, Code, Text) ->
    #{jsonrpc => <<"2.0">>, id => Id, error => #{code => Code, message => Text}}.
