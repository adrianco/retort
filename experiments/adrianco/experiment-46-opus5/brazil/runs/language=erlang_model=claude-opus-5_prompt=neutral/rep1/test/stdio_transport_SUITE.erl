%%%-------------------------------------------------------------------
%%% @doc Feature: stdio transport.
%%%
%%% Context: an MCP client launches the server as a subprocess and talks
%%% newline delimited JSON over its stdin/stdout.  This suite drives the
%%% real escript through an Erlang port, which is the only way to prove
%%% the parts a unit test cannot reach: that stdout carries protocol
%%% messages *only* (no log lines, no progress output) and that UTF-8
%%% bytes are not mangled by the io system.
%%%
%%% The suite skips itself if the escript has not been built, so
%%% `rebar3 ct' works on a fresh checkout; `make check' builds it first.
%%% @end
%%%-------------------------------------------------------------------
-module(stdio_transport_SUITE).

-compile([export_all, nowarn_export_all]).

-include_lib("common_test/include/ct.hrl").
-include_lib("stdlib/include/assert.hrl").

-import(bsmcp_bdd, [feature/1, scenario/1, given/2, when_/2, then/2, and_/2]).

all() ->
    [a_full_session_over_stdio].

init_per_suite(Config) ->
    case escript_path() of
        {ok, Path} -> [{escript, Path} | Config];
        error -> {skip, "escript not built: run rebar3 escriptize"}
    end.

end_per_suite(_Config) ->
    ok.

%%--------------------------------------------------------------------

a_full_session_over_stdio(Config) ->
    feature("stdio transport"),
    scenario("A client runs a whole session against the executable"),
    Escript = ?config(escript, Config),
    Requests = given("a handshake followed by two tool calls", fun() ->
        [#{jsonrpc => <<"2.0">>, id => 1, method => <<"initialize">>,
           params => #{<<"protocolVersion">> => <<"2025-06-18">>,
                       <<"capabilities">> => #{}}},
         #{jsonrpc => <<"2.0">>, method => <<"notifications/initialized">>},
         #{jsonrpc => <<"2.0">>, id => 2, method => <<"tools/call">>,
           params => #{<<"name">> => <<"team_profile">>,
                       <<"arguments">> => #{<<"team">> => <<"Gremio">>}}},
         #{jsonrpc => <<"2.0">>, id => 3, method => <<"tools/call">>,
           params => #{<<"name">> => <<"standings">>,
                       <<"arguments">> => #{<<"competition">> => <<"serie a">>,
                                            <<"season">> => 2019}}}]
    end),
    Lines = when_("I pipe them into the executable", fun() ->
        run_session(Escript, Requests, ?config(priv_dir, Config))
    end),
    then("stdout contains exactly one JSON message per request", fun() ->
        ct:log("stdout lines: ~p", [length(Lines)]),
        length(Lines) =:= 3
    end),
    Decoded = and_("every line is valid JSON-RPC", fun() ->
        [begin
             {ok, D} = bsmcp_json:decode(L),
             ?assertEqual(<<"2.0">>, maps:get(<<"jsonrpc">>, D)),
             D
         end || L <- Lines]
    end),
    then("the notification produced no output", fun() ->
        [maps:get(<<"id">>, D) || D <- Decoded] =:= [1, 2, 3]
    end),
    and_("the accented club name survived the pipe", fun() ->
        [_, Profile | _] = Decoded,
        Structured = maps:get(<<"structuredContent">>, maps:get(<<"result">>, Profile)),
        maps:get(<<"name">>, maps:get(<<"team">>, Structured)) =:= <<"Grêmio"/utf8>>
    end),
    and_("the standings call came back complete", fun() ->
        [_, _, Table] = Decoded,
        Structured = maps:get(<<"structuredContent">>, maps:get(<<"result">>, Table)),
        maps:get(<<"champion">>, Structured) =:= <<"Flamengo-RJ">>
    end).

%%--------------------------------------------------------------------

%% A port has no half close, so the requests are written to a file and
%% redirected into the process: the server then sees a real EOF on stdin
%% and exits, exactly as it would when a client disconnects.
run_session(Escript, Requests, PrivDir) ->
    File = filename:join(PrivDir, "session.jsonl"),
    ok = file:write_file(File, [[bsmcp_json:encode(R), $\n] || R <- Requests]),
    Cmd = lists:flatten(io_lib:format("~ts serve < ~ts", [Escript, File])),
    Port = open_port({spawn, Cmd},
                     [binary, exit_status, use_stdio, {cd, project_root()}]),
    Output = collect(Port, <<>>),
    [L || L <- binary:split(Output, <<"\n">>, [global, trim_all]), L =/= <<>>].

collect(Port, Acc) ->
    receive
        {Port, {data, Data}} ->
            collect(Port, <<Acc/binary, Data/binary>>);
        {Port, {exit_status, _}} ->
            Acc
    after 60000 ->
            try port_close(Port) catch _:_ -> ok end,
            ct:fail(stdio_session_timeout)
    end.

escript_path() ->
    Path = filename:join([project_root(), "_build", "default", "bin", "bsmcp"]),
    case filelib:is_regular(Path) of
        true -> {ok, Path};
        false -> error
    end.

project_root() ->
    case code:lib_dir(bsmcp) of
        {error, _} ->
            {ok, Cwd} = file:get_cwd(),
            Cwd;
        Dir ->
            %% _build/<profile>/lib/bsmcp -> project root
            lists:foldl(fun(_, D) -> filename:dirname(D) end, Dir, lists:seq(1, 4))
    end.