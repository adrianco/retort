%%%-------------------------------------------------------------------
%%% @doc Feature: stdio transport, end to end
%%%
%%% Starts the built escript as a real MCP client would - as a child
%%% process speaking newline delimited JSON-RPC on stdin/stdout - and
%%% runs a complete session through it.
%%% @end
%%%-------------------------------------------------------------------
-module(mcp_stdio_SUITE).

-compile([export_all, nowarn_export_all]).

-include_lib("common_test/include/ct.hrl").
-include_lib("stdlib/include/assert.hrl").

-define(STARTUP_TIMEOUT, 60000).

all() ->
    [a_full_session_over_stdio,
     stdout_carries_only_protocol_messages].

init_per_suite(Config) ->
    bdd:feature("stdio transport"),
    case escript_path() of
        {ok, Path} -> [{escript, Path} | Config];
        error -> {skip, "escript not built - run: rebar3 escriptize"}
    end.

end_per_suite(_Config) -> ok.

%%--------------------------------------------------------------------
a_full_session_over_stdio(Config) ->
    bdd:scenario("A client initialises the server and calls a tool"),
    Escript = ?config(escript, Config),
    bdd:given("the server is started as a child process", fun() -> ok end),
    Responses =
        bdd:'when'("the client sends initialize, a notification and two tool calls",
                   fun() ->
                           session(Escript,
                                   [#{jsonrpc => <<"2.0">>, id => 1,
                                      method => <<"initialize">>,
                                      params => #{protocolVersion => <<"2025-06-18">>,
                                                  capabilities => #{},
                                                  clientInfo => #{name => <<"ct">>,
                                                                  version => <<"1">>}}},
                                    #{jsonrpc => <<"2.0">>,
                                      method => <<"notifications/initialized">>},
                                    #{jsonrpc => <<"2.0">>, id => 2,
                                      method => <<"tools/list">>},
                                    #{jsonrpc => <<"2.0">>, id => 3,
                                      method => <<"tools/call">>,
                                      params => #{name => <<"ask">>,
                                                  arguments =>
                                                      #{question =>
                                                            <<"Who won the 2019 "
                                                              "Brasileirao?">>}}}])
                   end),
    bdd:then("three responses come back, one per request",
             fun() ->
                     ?assertEqual(3, length(Responses)),
                     ?assertEqual([1, 2, 3], [maps:get(<<"id">>, R) || R <- Responses])
             end),
    bdd:'and'("the handshake names the server",
              fun() ->
                      [#{<<"result">> := R} | _] = Responses,
                      ?assertMatch(#{<<"name">> := <<"brazilian-soccer">>},
                                   maps:get(<<"serverInfo">>, R))
              end),
    bdd:'and'("the tool list is not empty",
              fun() ->
                      [_, #{<<"result">> := #{<<"tools">> := Tools}} | _] = Responses,
                      ?assert(length(Tools) >= 15)
              end),
    bdd:'and'("the answer to the question names the champion",
              fun() ->
                      [_, _, #{<<"result">> := Result}] = Responses,
                      [#{<<"text">> := Text}] = maps:get(<<"content">>, Result),
                      ?assertNotEqual(nomatch, binary:match(Text, <<"Flamengo">>))
              end).

%%--------------------------------------------------------------------
stdout_carries_only_protocol_messages(Config) ->
    bdd:scenario("Nothing but JSON-RPC is written to stdout"),
    Escript = ?config(escript, Config),
    Lines = bdd:'when'("the client sends one request",
                       fun() ->
                               raw_session(Escript,
                                           [#{jsonrpc => <<"2.0">>, id => 1,
                                              method => <<"ping">>}])
                       end),
    bdd:then("every line of stdout is a JSON-RPC message",
             fun() ->
                     ?assert(length(Lines) >= 1),
                     lists:foreach(
                       fun(Line) ->
                               ?assertMatch({ok, #{<<"jsonrpc">> := <<"2.0">>}},
                                            br_json:decode(Line))
                       end, Lines)
             end).

%%====================================================================
%% Helpers
%%====================================================================

escript_path() ->
    Candidates = [filename:join([code:lib_dir(br_soccer), "..", "..", "..",
                                 "default", "bin", "br_soccer_mcp"]),
                  "_build/default/bin/br_soccer_mcp"],
    case [P || P <- Candidates, filelib:is_regular(P)] of
        [Path | _] -> {ok, Path};
        [] -> error
    end.

session(Escript, Messages) ->
    [begin {ok, Decoded} = br_json:decode(Line), Decoded end
     || Line <- raw_session(Escript, Messages)].

%% Feed the messages to the escript on stdin and collect stdout lines.
%%
%% The messages go through a file piped into the server so that stdin
%% reaches end of file and the server shuts down by itself, exactly as
%% it does when an MCP client disconnects.
raw_session(Escript, Messages) ->
    InputFile = filename:join(temp_dir(), "mcp_stdio_input.jsonl"),
    ok = file:write_file(InputFile, [[br_json:encode(M), $\n] || M <- Messages]),
    Command = lists:flatten(["cat ", InputFile, " | ", Escript, " serve"]),
    Port = open_port({spawn, Command}, [binary, exit_status, use_stdio]),
    try
        Output = collect(Port, <<>>),
        [L || L <- binary:split(Output, <<"\n">>, [global]), L =/= <<>>]
    after
        file:delete(InputFile)
    end.

collect(Port, Acc) ->
    receive
        {Port, {data, Data}} -> collect(Port, <<Acc/binary, Data/binary>>);
        {Port, {exit_status, _}} -> Acc
    after ?STARTUP_TIMEOUT ->
            ct:fail(timeout_waiting_for_server)
    end.

temp_dir() ->
    case os:getenv("TMPDIR") of
        false -> "/tmp";
        Dir -> Dir
    end.
