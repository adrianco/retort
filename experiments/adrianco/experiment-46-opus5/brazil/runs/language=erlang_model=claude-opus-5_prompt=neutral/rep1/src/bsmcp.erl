%%%-------------------------------------------------------------------
%%% @doc Command line entry point (also the escript main module).
%%%
%%% Context: `bsmcp serve' is what an MCP client launches - it speaks
%%% JSON-RPC over stdin/stdout and prints nothing else.  The other
%%% commands exist so the same code can be exercised from a shell:
%%%
%%%   bsmcp summary
%%%   bsmcp tools
%%%   bsmcp call standings '{"competition":"serie a","season":2019}'
%%%   bsmcp rpc '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
%%% @end
%%%-------------------------------------------------------------------
-module(bsmcp).

-export([main/1, start/0, serve/0]).

-spec main([string()]) -> ok.
main([]) ->
    serve();
main(["serve" | _]) ->
    serve();
main(["summary" | _]) ->
    start(),
    out(bsmcp_format:render(dataset_summary, bsmcp_query:dataset_summary()));
main(["tools" | _]) ->
    [out(io_lib:format("~-22ts ~ts", [maps:get(name, T), first_sentence(maps:get(description, T))]))
     || T <- bsmcp_tools:list()],
    ok;
main(["call", Tool]) ->
    main(["call", Tool, "{}"]);
main(["call", Tool, Json | Rest]) ->
    start(),
    case bsmcp_json:decode(unicode:characters_to_binary(Json, utf8, utf8)) of
        {ok, Args} when is_map(Args) ->
            case bsmcp_tools:call(unicode:characters_to_binary(Tool, utf8, utf8), Args) of
                {ok, Structured, Text} -> emit(Text, Structured, Rest);
                {error, Structured, Text} -> emit(Text, Structured, Rest)
            end;
        _ ->
            out(<<"Arguments must be a JSON object">>),
            halt(2)
    end;
main(["rpc", Json | _]) ->
    start(),
    case bsmcp_server:handle_binary(unicode:characters_to_binary(Json, utf8, utf8)) of
        noreply -> ok;
        {reply, Response} -> out(Response)
    end;
main(_) ->
    out(<<"usage: bsmcp [serve | summary | tools | call <tool> <json> [--json] | rpc <json>]">>),
    halt(2).

emit(Text, Structured, Rest) ->
    case lists:member("--json", Rest) of
        true -> out(bsmcp_json:encode(Structured));
        false -> out(Text)
    end.

-spec serve() -> ok.
serve() ->
    bsmcp_stdio:serve().

-spec start() -> ok.
start() ->
    {ok, _} = application:ensure_all_started(bsmcp),
    ok.

out(IoData) ->
    %% force UTF-8 on the device: the default depends on the locale, and
    %% a latin1 device would mangle club names on the way out
    _ = io:setopts(standard_io, [{encoding, utf8}]),
    io:put_chars(standard_io, [unicode:characters_to_binary(IoData, utf8, utf8), $\n]).

first_sentence(Desc) ->
    case binary:split(Desc, <<". ">>) of
        [First | _] -> First;
        _ -> Desc
    end.
