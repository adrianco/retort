%% MCP (Model Context Protocol) server over stdio, JSON-RPC 2.0, newline-delimited.
-module(brsoccer).
-export([main/1, handle/1, serve/2]).

-define(PROTOCOL, <<"2024-11-05">>).

main(_Args) ->
    brsoccer_data:load(),
    ok = io:setopts(standard_io, [binary, {encoding, unicode}]),
    serve(standard_io, standard_io).

serve(In, Out) ->
    case io:get_line(In, "") of
        eof -> ok;
        {error, _} -> ok;
        Line ->
            case string:trim(Line) of
                <<>> -> ok;
                L -> case handle_line(L) of
                         noreply -> ok;
                         Resp -> io:put_chars(Out, iolist_to_binary([json:encode(Resp), $\n]))
                     end
            end,
            serve(In, Out)
    end.

handle_line(L) ->
    try json:decode(L) of
        Req -> handle(Req)
    catch _:_ ->
        err(null, -32700, <<"Parse error">>)
    end.

%% Handle one decoded JSON-RPC message; returns a response map or noreply.
handle(#{<<"method">> := M} = Req) ->
    Id = maps:get(<<"id">>, Req, undefined),
    Params = maps:get(<<"params">>, Req, #{}),
    case {Id, dispatch(M, Params)} of
        {undefined, _} -> noreply;
        {_, {ok, R}} -> #{jsonrpc => <<"2.0">>, id => Id, result => R};
        {_, {error, C, Msg}} -> err(Id, C, Msg)
    end;
handle(_) -> err(null, -32600, <<"Invalid Request">>).

err(Id, C, Msg) -> #{jsonrpc => <<"2.0">>, id => Id, error => #{code => C, message => Msg}}.

dispatch(<<"initialize">>, _) ->
    {ok, #{protocolVersion => ?PROTOCOL,
           capabilities => #{tools => #{}},
           serverInfo => #{name => <<"brazilian-soccer">>, version => <<"1.0.0">>}}};
dispatch(<<"notifications/", _/binary>>, _) -> {ok, #{}};
dispatch(<<"ping">>, _) -> {ok, #{}};
dispatch(<<"tools/list">>, _) -> {ok, #{tools => brsoccer_tools:list()}};
dispatch(<<"tools/call">>, #{<<"name">> := N} = P) ->
    {Text, IsErr} = case brsoccer_tools:call(N, maps:get(<<"arguments">>, P, #{})) of
                        {ok, T} -> {T, false};
                        {error, T} -> {T, true}
                    end,
    {ok, #{content => [#{type => <<"text">>, text => Text}], isError => IsErr}};
dispatch(M, _) -> {error, -32601, <<"Method not found: ", M/binary>>}.
