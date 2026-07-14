%%% ===================================================================
%%% Brazilian Soccer MCP Server - stdio transport / entry point
%%%
%%% Context: Runs the MCP server over the standard stdio transport, the
%%% way an MCP client (e.g. Claude Desktop) launches it: newline
%%% delimited JSON-RPC messages are read from stdin and responses are
%%% written to stdout. Requests without an `id' (JSON-RPC notifications)
%%% receive no response, as required by the spec.
%%%
%%% Usage:
%%%   * as an escript:  `bsoccer-mcp [data_dir]'  (see rebar.config)
%%%   * from a shell:   `bsoccer_stdio:start("data/kaggle")'
%%% ===================================================================
-module(bsoccer_stdio).

-export([main/1, start/0, start/1]).

%% escript entry point.
main(Args) ->
    DataDir = case Args of
                  [Dir | _] -> Dir;
                  [] -> "data/kaggle"
              end,
    start(DataDir).

start() ->
    start("data/kaggle").

start(DataDir) ->
    application:set_env(bsoccer, data_dir, DataDir),
    {ok, _} = application:ensure_all_started(bsoccer),
    ok = bsoccer_data:ready(),
    io:setopts(standard_io, [binary, {encoding, utf8}]),
    loop().

loop() ->
    case io:get_line(standard_io, <<>>) of
        eof ->
            ok;
        {error, _Reason} ->
            ok;
        Line ->
            handle_line(Line),
            loop()
    end.

handle_line(Line) ->
    case string:trim(Line) of
        <<>> ->
            ok;
        Trimmed ->
            case is_notification(Trimmed) of
                true ->
                    ok;  %% notifications get no reply
                false ->
                    Resp = bsoccer_mcp:handle(Trimmed),
                    io:put_chars(standard_io, [Resp, $\n])
            end
    end.

%% A request is a notification when it carries no "id" member.
is_notification(Bin) ->
    try json:decode(Bin) of
        Map when is_map(Map) -> not maps:is_key(<<"id">>, Map);
        _ -> false
    catch
        _:_ -> false
    end.
