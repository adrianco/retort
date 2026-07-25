%%%-------------------------------------------------------------------
%%% @doc MCP stdio transport.
%%%
%%% Reads newline delimited JSON-RPC messages from stdin and writes the
%%% responses to stdout, which is the transport every MCP client uses
%%% for a locally launched server.  Nothing else may be written to
%%% stdout, so logging is redirected to stderr before the loop starts.
%%% @end
%%%-------------------------------------------------------------------
-module(br_mcp_stdio).

-export([run/0, loop/0, configure_logging/0]).

%%--------------------------------------------------------------------
%% @doc Serve until stdin closes.
-spec run() -> ok.
run() ->
    configure_logging(),
    ok = io:setopts(standard_io, [binary]),
    loop().

%%--------------------------------------------------------------------
%% @doc Send log output to stderr: stdout carries the protocol.
-spec configure_logging() -> ok.
configure_logging() ->
    _ = logger:remove_handler(default),
    _ = logger:add_handler(stderr, logger_std_h,
                           #{config => #{type => standard_error},
                             level => notice,
                             formatter => {logger_formatter,
                                           #{single_line => true,
                                             template => [level, ": ", msg, "\n"]}}}),
    ok.

%%--------------------------------------------------------------------
-spec loop() -> ok.
loop() ->
    case io:get_line(standard_io, <<>>) of
        eof -> ok;
        {error, Reason} ->
            logger:error("stdin read error: ~p", [Reason]),
            ok;
        Line ->
            case br_text:trim(iolist_to_binary(Line)) of
                <<>> -> ok;
                Message -> respond(Message)
            end,
            loop()
    end.

respond(Message) ->
    case br_mcp_server:handle_message(Message) of
        noreply -> ok;
        {reply, Response} ->
            io:put_chars(standard_io, [Response, $\n])
    end.
