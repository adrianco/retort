%% @doc stdio transport for the MCP server.
%%
%% Reads newline-delimited JSON-RPC messages from standard input, hands
%% each to {@link bsmcp_mcp}, and writes newline-delimited responses to
%% standard output. Diagnostics go to standard error so they never
%% corrupt the protocol stream.
-module(bsmcp_server).

-export([main/1, run/1, load_store/1, process_line/2]).

%% @doc escript / CLI entry point. Args may contain the data directory.
-spec main([string()]) -> ok.
main(Args) ->
    Dir = data_dir(Args),
    log("Loading Brazilian soccer data from ~s ...", [Dir]),
    Store = load_store(Dir),
    log("Loaded ~p matches and ~p players. Ready.",
        [length(maps:get(matches, Store)), length(maps:get(players, Store))]),
    run(Store).

data_dir([Dir | _]) -> Dir;
data_dir([]) -> bsmcp_data:default_dir().

%% @doc Load all datasets into an in-memory store.
-spec load_store(file:name_all()) -> map().
load_store(Dir) ->
    #{matches => bsmcp_data:load_matches(Dir),
      players => bsmcp_data:load_players(Dir)}.

%% @doc Read/serve loop over stdin until EOF.
-spec run(map()) -> ok.
run(Store) ->
    case io:get_line(standard_io, "") of
        eof ->
            ok;
        {error, _} ->
            ok;
        Line ->
            case process_line(unicode:characters_to_binary(Line), Store) of
                {ok, Out} ->
                    io:put_chars(standard_io, [Out, $\n]);
                none ->
                    ok
            end,
            run(Store)
    end.

%% @doc Process a single input line, returning the response bytes to write
%% (without trailing newline) or `none' if nothing should be sent.
-spec process_line(binary(), map()) -> {ok, binary()} | none.
process_line(Line, Store) ->
    case string:trim(Line) of
        <<>> ->
            none;
        Trimmed ->
            case safe_decode(Trimmed) of
                {ok, Req} ->
                    handle(Req, Store);
                error ->
                    {ok, bsmcp_mcp:encode(parse_error())}
            end
    end.

handle(Req, Store) ->
    case bsmcp_mcp:handle_request(Req, Store) of
        {reply, Resp} -> {ok, bsmcp_mcp:encode(Resp)};
        noreply -> none
    end.

safe_decode(Bin) ->
    try {ok, bsmcp_mcp:decode(Bin)}
    catch _:_ -> error
    end.

parse_error() ->
    #{<<"jsonrpc">> => <<"2.0">>, <<"id">> => null,
      <<"error">> => #{<<"code">> => -32700,
                       <<"message">> => <<"Parse error">>}}.

log(Fmt, Args) ->
    io:format(standard_error, Fmt ++ "~n", Args).
