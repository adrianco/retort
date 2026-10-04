%% escript entry point: MCP server over stdio (one JSON message per line).
-module(brsoccer).
-export([main/1]).

main(_Args) ->
    ok = io:setopts(standard_io, [binary, {encoding, unicode}]),
    case bs_data:load(bs_data:data_dir()) of
        ok -> loop();
        {error, Reason} ->
            io:format(standard_error, "brsoccer_mcp: cannot load data: ~p~n"
                      "Set BRSOCCER_DATA_DIR to the directory containing the CSV files.~n", [Reason]),
            halt(1)
    end.

loop() ->
    case io:get_line(standard_io, "") of
        eof -> ok;
        {error, _} -> ok;
        Line ->
            case bs_mcp:handle_line(Line) of
                {reply, Json} -> io:put_chars(standard_io, [Json, $\n]);
                noreply -> ok
            end,
            loop()
    end.
