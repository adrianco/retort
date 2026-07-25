%% MCP stdio transport: newline-delimited JSON-RPC on stdin/stdout.
%% Diagnostics go to stderr (stdout must carry only protocol messages).
-module(bsmcp_server).

-export([main/1, run/1, handle_line/1]).

main(Args) ->
    Dir = case Args of
              [D | _] -> D;
              [] -> bsmcp_data:default_dir()
          end,
    run(Dir).

run(Dir) ->
    %% Binary mode + unicode device encoding: get_line returns UTF-8 binaries
    %% for json:decode, and put_chars writes UTF-8 chardata back out as UTF-8.
    ok = io:setopts(standard_io, [binary, {encoding, unicode}]),
    log("Loading Brazilian soccer data from ~ts ...", [Dir]),
    T0 = erlang:monotonic_time(millisecond),
    case bsmcp_data:load(Dir) of
        {ok, Summary} ->
            log("Loaded ~b matches, ~b players, ~b teams in ~b ms "
                "(~b duplicates skipped)",
                [maps:get(matches, Summary), maps:get(players, Summary),
                 maps:get(teams, Summary),
                 erlang:monotonic_time(millisecond) - T0,
                 maps:get(duplicates_skipped, Summary)]),
            loop();
        {error, Reason} ->
            log("Failed to load data from ~ts: ~p", [Dir, Reason]),
            erlang:halt(1)
    end.

loop() ->
    case io:get_line(standard_io, "") of
        eof ->
            log("stdin closed, shutting down", []),
            ok;
        {error, Reason} ->
            log("stdin error: ~p", [Reason]),
            ok;
        Line ->
            case handle_line(Line) of
                noreply -> ok;
                Reply -> io:put_chars(standard_io, [Reply, $\n])
            end,
            loop()
    end.

%% One line in -> encoded JSON reply (iodata) or noreply. Exported for tests.
-spec handle_line(binary() | string()) -> iodata() | noreply.
handle_line(Line) ->
    Bin = string:trim(iolist_to_binary([Line])),
    case Bin of
        <<>> ->
            noreply;
        _ ->
            Result = try {ok, json:decode(Bin)}
                     catch _:_ -> decode_error
                     end,
            case Result of
                decode_error ->
                    json:encode(bsmcp_rpc:parse_error_reply());
                {ok, Msg} ->
                    case bsmcp_rpc:handle(Msg) of
                        noreply -> noreply;
                        {reply, Reply} -> json:encode(Reply)
                    end
            end
    end.

log(Fmt, Args) ->
    io:format(standard_error, "[bsmcp] " ++ Fmt ++ "~n", Args).
