%% @doc MCP JSON-RPC 2.0 request handling.
%%
%% `handle_request/2' is a pure function mapping a decoded request map and
%% a data store to either `{reply, ResponseMap}' or `noreply' (for
%% notifications). `encode/1' and `decode/1' wrap the OTP `json' module.
-module(bsmcp_mcp).

-export([handle_request/2, encode/1, decode/1]).

-define(PROTOCOL_VERSION, <<"2024-11-05">>).
-define(SERVER_NAME, <<"brazilian-soccer-mcp">>).
-define(SERVER_VERSION, <<"0.1.0">>).

%% @doc Handle one decoded JSON-RPC request.
-spec handle_request(map(), map()) -> {reply, map()} | noreply.
handle_request(Req, Store) ->
    Method = maps:get(<<"method">>, Req, undefined),
    case maps:find(<<"id">>, Req) of
        error ->
            %% No id => notification; never replies.
            noreply;
        {ok, Id} ->
            {reply, reply(Id, dispatch(Method, Req, Store))}
    end.

dispatch(<<"initialize">>, _Req, _Store) ->
    {ok, #{<<"protocolVersion">> => ?PROTOCOL_VERSION,
           <<"capabilities">> => #{<<"tools">> => #{}},
           <<"serverInfo">> => #{<<"name">> => ?SERVER_NAME,
                                 <<"version">> => ?SERVER_VERSION}}};
dispatch(<<"tools/list">>, _Req, _Store) ->
    {ok, #{<<"tools">> => [tool_json(T) || T <- bsmcp_tools:list()]}};
dispatch(<<"tools/call">>, Req, Store) ->
    Params = maps:get(<<"params">>, Req, #{}),
    Name = maps:get(<<"name">>, Params, <<>>),
    Args = maps:get(<<"arguments">>, Params, #{}),
    {ok, call_result(Name, Args, Store)};
dispatch(<<"ping">>, _Req, _Store) ->
    {ok, #{}};
dispatch(Method, _Req, _Store) ->
    {error, -32601, <<"Method not found: ", (to_bin(Method))/binary>>}.

call_result(Name, Args, Store) ->
    case safe_call(Name, Args, Store) of
        {ok, Text} ->
            #{<<"content">> => [text_content(Text)], <<"isError">> => false};
        {error, Reason} ->
            #{<<"content">> => [text_content(Reason)], <<"isError">> => true}
    end.

%% Guard against crashes inside a tool so the protocol layer stays alive.
safe_call(Name, Args, Store) ->
    try bsmcp_tools:call(Name, Args, Store)
    catch
        Class:Why ->
            {error, iolist_to_binary(
                      ["Tool error: ", io_lib:format("~p:~p", [Class, Why])])}
    end.

text_content(Text) ->
    #{<<"type">> => <<"text">>, <<"text">> => to_bin(Text)}.

%% --- response shaping -------------------------------------------------

reply(Id, {ok, Result}) ->
    #{<<"jsonrpc">> => <<"2.0">>, <<"id">> => Id, <<"result">> => Result};
reply(Id, {error, Code, Message}) ->
    #{<<"jsonrpc">> => <<"2.0">>, <<"id">> => Id,
      <<"error">> => #{<<"code">> => Code, <<"message">> => Message}}.

%% Tool catalog maps use atom keys; convert to the binary-keyed shape the
%% JSON encoder and clients expect.
tool_json(T) ->
    #{<<"name">> => maps:get(name, T),
      <<"description">> => maps:get(description, T),
      <<"inputSchema">> => maps:get(inputSchema, T)}.

%% --- JSON codec -------------------------------------------------------

-spec encode(term()) -> binary().
encode(Term) ->
    iolist_to_binary(json:encode(Term)).

-spec decode(binary()) -> term().
decode(Bin) ->
    json:decode(Bin).

to_bin(B) when is_binary(B) -> B;
to_bin(L) when is_list(L) -> iolist_to_binary(L);
to_bin(undefined) -> <<"undefined">>;
to_bin(A) when is_atom(A) -> atom_to_binary(A, utf8).
