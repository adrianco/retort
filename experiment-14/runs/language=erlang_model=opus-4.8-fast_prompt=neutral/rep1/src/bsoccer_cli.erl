%%% =====================================================================
%%% bsoccer_cli — escript entry point and MCP stdio transport.
%%%
%%% Loads the datasets into the knowledge graph (bsoccer_data) and then runs
%%% the newline-delimited JSON-RPC loop that is the standard MCP stdio
%%% transport: read one JSON object per line from stdin, hand it to
%%% bsoccer_mcp, and write any response as a single line to stdout. Logs and
%%% load progress go to stderr so they never corrupt the protocol stream.
%%%
%%% Usage:
%%%   bsoccer            — serve MCP over stdio (default data dir data/kaggle)
%%%   bsoccer <data_dir> — serve using a custom data directory
%%%   bsoccer --selftest — load data, print a summary, run a couple of demo
%%%                        queries, and exit (handy smoke test without a client)
%%% =====================================================================
-module(bsoccer_cli).

-export([main/1, serve/0]).

main(Args) ->
    %% Read/write UTF-8 on stdio: get_line returns the raw UTF-8 bytes as a
    %% binary (ready for json:decode) and put_chars emits UTF-8 binaries from
    %% json:encode verbatim. (Using latin1 here would double-encode accented
    %% team names like "Grêmio" / "Brasileirão" on the way in or out.)
    ok = io:setopts(standard_io, [binary, {encoding, unicode}]),
    case Args of
        ["--selftest" | Rest] ->
            DataDir = data_dir(Rest),
            {ok, _} = bsoccer_data:ensure_started(DataDir),
            selftest();
        _ ->
            DataDir = data_dir(Args),
            log("loading Brazilian soccer data from ~s ...", [DataDir]),
            {ok, _} = bsoccer_data:ensure_started(DataDir),
            S = bsoccer_data:stats(),
            log("loaded ~p matches and ~p players; MCP server ready on stdio",
                [maps:get(matches, S), maps:get(players, S)]),
            serve()
    end.

data_dir([Dir | _]) -> Dir;
data_dir([]) -> bsoccer_data:default_data_dir().

%% --- stdio JSON-RPC loop --------------------------------------------------

serve() ->
    case read_line() of
        eof ->
            ok;
        Line ->
            handle_line(Line),
            serve()
    end.

handle_line(Line) ->
    case bsoccer_util:trim(Line) of
        <<>> ->
            ok;
        Trimmed ->
            case decode(Trimmed) of
                {ok, Msg} ->
                    case bsoccer_mcp:handle_message(Msg) of
                        {reply, Response} -> write_json(Response);
                        noreply -> ok
                    end;
                {error, _} ->
                    write_json(parse_error())
            end
    end.

decode(Bin) ->
    try {ok, json:decode(Bin)}
    catch _:_ -> {error, parse_error}
    end.

parse_error() ->
    #{<<"jsonrpc">> => <<"2.0">>, <<"id">> => null,
      <<"error">> => #{<<"code">> => -32700, <<"message">> => <<"parse error">>}}.

%% --- raw byte IO ----------------------------------------------------------

read_line() ->
    case io:get_line(standard_io, <<>>) of
        eof -> eof;
        {error, _} -> eof;
        Data -> to_bin(Data)
    end.

to_bin(B) when is_binary(B) -> B;
to_bin(L) when is_list(L) -> list_to_binary(L).

write_json(Map) ->
    Json = json:encode(Map),
    %% On the unicode-encoded device, put_chars/2 emits the UTF-8 bytes from
    %% json:encode/1 correctly. One JSON message per line (newline-delimited
    %% framing, as per the MCP stdio transport).
    io:put_chars(standard_io, [Json, $\n]).

%% --- self-test ------------------------------------------------------------

selftest() ->
    Summary = bsoccer_query:data_summary(#{}),
    log("~s", [maps:get(text, Summary)]),
    Demo = [{<<"search_matches">>, #{<<"team">> => <<"Flamengo">>,
                                     <<"opponent">> => <<"Fluminense">>,
                                     <<"limit">> => 3}},
            {<<"standings">>, #{<<"season">> => 2019}},
            {<<"search_players">>, #{<<"nationality">> => <<"Brazil">>,
                                     <<"limit">> => 3}}],
    lists:foreach(
      fun({Tool, Args}) ->
              R = bsoccer_mcp:call_tool(Tool, Args),
              [#{<<"text">> := Text} | _] = maps:get(<<"content">>, R),
              log("~n=== ~s ===~n~s", [Tool, Text])
      end, Demo),
    ok.

log(Format, Args) ->
    io:format(standard_error, Format ++ "~n", Args).
