%%%-------------------------------------------------------------------
%%% @doc MCP stdio transport: newline delimited JSON-RPC.
%%%
%%% Context: stdout carries protocol messages only, so the loop puts the
%%% standard_io device into binary UTF-8 mode (the io system decodes the
%%% binaries it is handed as UTF-8 and re-encodes them for the device;
%%% with the default latin1 device encoding "Grêmio" would leave the
%%% process as a single 0xEA byte and break the JSON) and redirects the
%%% logger to stderr before the first message is read.  One message per
%%% line, exactly as the MCP stdio transport specifies.
%%% @end
%%%-------------------------------------------------------------------
-module(bsmcp_stdio).

-export([serve/0, loop/0, loop/1]).

%% A client that sends undecodable bytes gets a parse error back, but a
%% device that keeps failing must not spin forever.
-define(MAX_CONSECUTIVE_ERRORS, 10).

-spec serve() -> ok.
serve() ->
    ok = io:setopts(standard_io, [binary, {encoding, utf8}]),
    redirect_logger(),
    ok = bsmcp_data:ensure_loaded(),
    loop().

-spec loop() -> ok.
loop() -> loop(0).

-spec loop(non_neg_integer()) -> ok.
loop(Errors) when Errors >= ?MAX_CONSECUTIVE_ERRORS ->
    ok;
loop(Errors) ->
    case io:get_line(standard_io, <<>>) of
        eof ->
            ok;
        {error, _Reason} ->
            {reply, Response} = bsmcp_server:handle_binary(<<"undecodable input">>),
            emit(Response),
            loop(Errors + 1);
        Line ->
            case strip(Line) of
                <<>> ->
                    ok;
                Message ->
                    case bsmcp_server:handle_binary(Message) of
                        noreply -> ok;
                        {reply, Response} -> emit(Response)
                    end
            end,
            loop(0)
    end.

emit(Response) ->
    io:put_chars(standard_io, [Response, $\n]).

strip(Line) when is_binary(Line) ->
    string:trim(Line, both, "\r\n \t");
strip(Line) ->
    strip(iolist_to_binary(Line)).

%% Any log line on stdout would corrupt the protocol stream.
redirect_logger() ->
    _ = logger:update_handler_config(default, #{config => #{type => standard_error}}),
    _ = logger:set_primary_config(level, warning),
    ok.
