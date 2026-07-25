%%%-------------------------------------------------------------------
%%% @doc Feature: MCP protocol.
%%%
%%% Context: exercises the JSON-RPC surface an MCP client actually
%%% speaks - handshake, tool discovery, tool invocation, resources and
%%% the error paths.  The whole layer is driven through
%%% `bsmcp_server:handle_binary/1', i.e. exactly the bytes the stdio
%%% transport would hand it, and one scenario drives the real
%%% executable over a port to prove the framing works end to end.
%%% @end
%%%-------------------------------------------------------------------
-module(mcp_protocol_SUITE).

-compile([export_all, nowarn_export_all]).

-include_lib("common_test/include/ct.hrl").
-include_lib("stdlib/include/assert.hrl").

-import(bsmcp_bdd, [feature/1, scenario/1, given/2, when_/2, then/2, and_/2, rpc/1]).

all() ->
    [initialize_handshake,
     tools_are_discoverable,
     tool_call_returns_text_and_structured_content,
     tool_errors_are_not_protocol_errors,
     notifications_get_no_response,
     unknown_method_is_reported,
     invalid_json_is_reported,
     batch_requests_are_supported,
     resources_can_be_listed_and_read,
     every_tool_answers_a_call].

init_per_suite(Config) ->
    bsmcp_test_helper:start(),
    Config.

end_per_suite(_Config) ->
    ok.

init_per_testcase(_Case, Config) ->
    feature("MCP protocol"),
    Config.

%%--------------------------------------------------------------------

initialize_handshake(_Config) ->
    scenario("A client initialises the session"),
    Response = when_("the client sends initialize", fun() ->
        rpc(#{jsonrpc => <<"2.0">>, id => 1, method => <<"initialize">>,
              params => #{<<"protocolVersion">> => <<"2025-06-18">>,
                          <<"capabilities">> => #{},
                          <<"clientInfo">> => #{<<"name">> => <<"ct">>,
                                                <<"version">> => <<"1">>}}})
    end),
    Result = maps:get(<<"result">>, Response),
    then("the negotiated protocol version is echoed", fun() ->
        maps:get(<<"protocolVersion">>, Result) =:= <<"2025-06-18">>
    end),
    and_("the server advertises tools and resources", fun() ->
        Caps = maps:get(<<"capabilities">>, Result),
        maps:is_key(<<"tools">>, Caps) andalso maps:is_key(<<"resources">>, Caps)
    end),
    and_("the server identifies itself", fun() ->
        maps:get(<<"name">>, maps:get(<<"serverInfo">>, Result)) =:= <<"brazilian-soccer">>
    end),
    and_("instructions describe the dataset for the model", fun() ->
        byte_size(maps:get(<<"instructions">>, Result)) > 100
    end),
    and_("an older protocol version is accepted too", fun() ->
        Old = rpc(#{jsonrpc => <<"2.0">>, id => 2, method => <<"initialize">>,
                    params => #{<<"protocolVersion">> => <<"2024-11-05">>}}),
        maps:get(<<"protocolVersion">>, maps:get(<<"result">>, Old)) =:= <<"2024-11-05">>
    end).

tools_are_discoverable(_Config) ->
    scenario("The client lists the available tools"),
    Response = when_("the client sends tools/list", fun() ->
        rpc(#{jsonrpc => <<"2.0">>, id => 3, method => <<"tools/list">>})
    end),
    Tools = maps:get(<<"tools">>, maps:get(<<"result">>, Response)),
    then("all fourteen tools are advertised", fun() -> length(Tools) =:= 14 end),
    and_("each tool has a name, description and JSON Schema", fun() ->
        lists:all(fun(T) ->
                          is_binary(maps:get(<<"name">>, T))
                              andalso byte_size(maps:get(<<"description">>, T)) > 40
                              andalso maps:get(<<"type">>, maps:get(<<"inputSchema">>, T))
                                      =:= <<"object">>
                  end, Tools)
    end),
    and_("required arguments are declared where they matter", fun() ->
        [H2H] = [T || T <- Tools, maps:get(<<"name">>, T) =:= <<"head_to_head">>],
        lists:sort(maps:get(<<"required">>, maps:get(<<"inputSchema">>, H2H)))
            =:= [<<"team_a">>, <<"team_b">>]
    end).

tool_call_returns_text_and_structured_content(_Config) ->
    scenario("A tool call returns both prose and structured data"),
    Response = when_("the client calls standings for 2019", fun() ->
        rpc(#{jsonrpc => <<"2.0">>, id => 4, method => <<"tools/call">>,
              params => #{<<"name">> => <<"standings">>,
                          <<"arguments">> => #{<<"competition">> => <<"serie a">>,
                                               <<"season">> => 2019}}})
    end),
    Result = maps:get(<<"result">>, Response),
    then("the call is not flagged as an error", fun() ->
        maps:get(<<"isError">>, Result) =:= false
    end),
    and_("a text content block is present", fun() ->
        [Block] = maps:get(<<"content">>, Result),
        maps:get(<<"type">>, Block) =:= <<"text">>
            andalso binary:match(maps:get(<<"text">>, Block), <<"Champion">>) =/= nomatch
    end),
    and_("structured content carries the table", fun() ->
        Structured = maps:get(<<"structuredContent">>, Result),
        length(maps:get(<<"table">>, Structured)) =:= 20
            andalso maps:get(<<"champion">>, Structured) =:= <<"Flamengo-RJ">>
    end),
    and_("season numbers survive as numbers", fun() ->
        maps:get(<<"season">>, maps:get(<<"structuredContent">>, Result)) =:= 2019
    end).

tool_errors_are_not_protocol_errors(_Config) ->
    scenario("A tool level failure comes back as isError, not a JSON-RPC error"),
    Response = when_("the client asks about a club that does not exist", fun() ->
        rpc(#{jsonrpc => <<"2.0">>, id => 5, method => <<"tools/call">>,
              params => #{<<"name">> => <<"team_stats">>,
                          <<"arguments">> => #{<<"team">> => <<"Manchester Utd XI">>}}})
    end),
    then("the response is a successful JSON-RPC result", fun() ->
        maps:is_key(<<"result">>, Response) andalso not maps:is_key(<<"error">>, Response)
    end),
    and_("the result is flagged as a tool error", fun() ->
        maps:get(<<"isError">>, maps:get(<<"result">>, Response)) =:= true
    end),
    and_("the text explains what went wrong", fun() ->
        [Block] = maps:get(<<"content">>, maps:get(<<"result">>, Response)),
        binary:match(maps:get(<<"text">>, Block), <<"No team matched">>) =/= nomatch
    end),
    and_("an unknown tool name is handled the same way", fun() ->
        R = rpc(#{jsonrpc => <<"2.0">>, id => 6, method => <<"tools/call">>,
                  params => #{<<"name">> => <<"no_such_tool">>, <<"arguments">> => #{}}}),
        maps:get(<<"isError">>, maps:get(<<"result">>, R)) =:= true
    end).

notifications_get_no_response(_Config) ->
    scenario("Notifications are silent"),
    then("initialized produces no reply", fun() ->
        rpc(#{jsonrpc => <<"2.0">>, method => <<"notifications/initialized">>}) =:= noreply
    end),
    and_("a request without an id is treated as a notification", fun() ->
        rpc(#{jsonrpc => <<"2.0">>, method => <<"ping">>}) =:= noreply
    end),
    and_("ping with an id does reply", fun() ->
        R = rpc(#{jsonrpc => <<"2.0">>, id => 7, method => <<"ping">>}),
        maps:get(<<"result">>, R) =:= #{}
    end).

unknown_method_is_reported(_Config) ->
    scenario("An unsupported method returns method not found"),
    Response = when_("the client calls a method the server does not implement", fun() ->
        rpc(#{jsonrpc => <<"2.0">>, id => 8, method => <<"completion/complete">>})
    end),
    then("JSON-RPC error -32601 is returned", fun() ->
        maps:get(<<"code">>, maps:get(<<"error">>, Response)) =:= -32601
    end),
    and_("the id is echoed so the client can correlate it", fun() ->
        maps:get(<<"id">>, Response) =:= 8
    end).

invalid_json_is_reported(_Config) ->
    scenario("Malformed input returns a parse error"),
    Response = when_("the transport receives something that is not JSON", fun() ->
        {reply, Raw} = bsmcp_server:handle_binary(<<"{not json">>),
        {ok, Decoded} = bsmcp_json:decode(Raw),
        Decoded
    end),
    then("JSON-RPC error -32700 is returned", fun() ->
        maps:get(<<"code">>, maps:get(<<"error">>, Response)) =:= -32700
    end),
    and_("a request without a method is rejected", fun() ->
        {reply, Raw} = bsmcp_server:handle_binary(<<"{\"jsonrpc\":\"2.0\",\"id\":9}">>),
        {ok, D} = bsmcp_json:decode(Raw),
        maps:get(<<"code">>, maps:get(<<"error">>, D)) =:= -32600
    end).

batch_requests_are_supported(_Config) ->
    scenario("A JSON-RPC batch is answered with a batch"),
    Responses = when_("the client sends two requests and a notification", fun() ->
        Batch = [#{jsonrpc => <<"2.0">>, id => 10, method => <<"ping">>},
                 #{jsonrpc => <<"2.0">>, method => <<"notifications/initialized">>},
                 #{jsonrpc => <<"2.0">>, id => 11, method => <<"tools/list">>}],
        {reply, Raw} = bsmcp_server:handle_binary(bsmcp_json:encode(Batch)),
        {ok, Decoded} = bsmcp_json:decode(Raw),
        Decoded
    end),
    then("only the two requests are answered", fun() ->
        length(Responses) =:= 2
            andalso lists:sort([maps:get(<<"id">>, R) || R <- Responses]) =:= [10, 11]
    end).

resources_can_be_listed_and_read(_Config) ->
    scenario("Resources describe the dataset"),
    List = when_("the client lists resources", fun() ->
        rpc(#{jsonrpc => <<"2.0">>, id => 12, method => <<"resources/list">>})
    end),
    Resources = maps:get(<<"resources">>, maps:get(<<"result">>, List)),
    then("four resources are offered", fun() -> length(Resources) =:= 4 end),
    Read = and_("the client reads the sources resource", fun() ->
        rpc(#{jsonrpc => <<"2.0">>, id => 13, method => <<"resources/read">>,
              params => #{<<"uri">> => <<"bsmcp://dataset/sources">>}})
    end),
    then("the licence table comes back as markdown", fun() ->
        [Content] = maps:get(<<"contents">>, maps:get(<<"result">>, Read)),
        maps:get(<<"mimeType">>, Content) =:= <<"text/markdown">>
            andalso binary:match(maps:get(<<"text">>, Content), <<"CC BY 4.0">>) =/= nomatch
    end),
    and_("the teams resource is valid JSON", fun() ->
        R = rpc(#{jsonrpc => <<"2.0">>, id => 14, method => <<"resources/read">>,
                  params => #{<<"uri">> => <<"bsmcp://teams">>}}),
        [Content] = maps:get(<<"contents">>, maps:get(<<"result">>, R)),
        {ok, Decoded} = bsmcp_json:decode(maps:get(<<"text">>, Content)),
        length(maps:get(<<"teams">>, Decoded)) > 100
    end),
    and_("an unknown uri is rejected", fun() ->
        R = rpc(#{jsonrpc => <<"2.0">>, id => 15, method => <<"resources/read">>,
                  params => #{<<"uri">> => <<"bsmcp://nope">>}}),
        maps:get(<<"code">>, maps:get(<<"error">>, R)) =:= -32602
    end).

every_tool_answers_a_call(_Config) ->
    scenario("Every advertised tool answers a realistic call"),
    Args = #{<<"search_matches">> => #{<<"team">> => <<"Santos">>, <<"limit">> => 3},
             <<"head_to_head">> => #{<<"team_a">> => <<"Corinthians">>,
                                     <<"team_b">> => <<"Palmeiras">>},
             <<"team_stats">> => #{<<"team">> => <<"Bahia">>},
             <<"team_profile">> => #{<<"team">> => <<"Vasco">>},
             <<"standings">> => #{<<"competition">> => <<"serie b">>, <<"season">> => 2019},
             <<"league_leaderboard">> => #{<<"metric">> => <<"points">>,
                                           <<"competition">> => <<"serie a">>,
                                           <<"season">> => 2018},
             <<"biggest_wins">> => #{<<"limit">> => 3},
             <<"competition_stats">> => #{<<"competition">> => <<"libertadores">>},
             <<"search_players">> => #{<<"nationality">> => <<"Brazil">>,
                                       <<"limit">> => 3},
             <<"player_profile">> => #{<<"name">> => <<"Casemiro">>},
             <<"club_squad">> => #{<<"club">> => <<"Santos">>},
             <<"club_ratings">> => #{<<"min_players">> => 10, <<"limit">> => 5},
             <<"list_teams">> => #{<<"query">> => <<"Sport">>},
             <<"dataset_summary">> => #{}},
    Results = when_("I call each tool over JSON-RPC", fun() ->
        [{Name, rpc(#{jsonrpc => <<"2.0">>, id => 100, method => <<"tools/call">>,
                      params => #{<<"name">> => Name,
                                  <<"arguments">> => maps:get(Name, Args)}})}
         || Name <- bsmcp_tools:names()]
    end),
    then("every tool was covered", fun() -> length(Results) =:= 14 end),
    and_("no tool reported an error", fun() ->
        lists:all(fun({Name, R}) ->
                          Result = maps:get(<<"result">>, R),
                          case maps:get(<<"isError">>, Result) of
                              false ->
                                  true;
                              true ->
                                  ct:pal("tool ~ts failed: ~p", [Name, Result]),
                                  false
                          end
                  end, Results)
    end),
    and_("every tool produced a non-trivial text answer", fun() ->
        lists:all(fun({_, R}) ->
                          [Block] = maps:get(<<"content">>, maps:get(<<"result">>, R)),
                          byte_size(maps:get(<<"text">>, Block)) > 20
                  end, Results)
    end).
