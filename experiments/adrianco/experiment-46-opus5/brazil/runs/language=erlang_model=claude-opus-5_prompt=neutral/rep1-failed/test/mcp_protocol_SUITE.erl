%%%-------------------------------------------------------------------
%%% @doc Feature: MCP protocol
%%%
%%% Drives the server the way a client does - raw JSON-RPC messages in,
%%% raw JSON out - including the stdio transport of the built escript.
%%% @end
%%%-------------------------------------------------------------------
-module(mcp_protocol_SUITE).

-compile([export_all, nowarn_export_all]).

-include_lib("common_test/include/ct.hrl").
-include_lib("stdlib/include/assert.hrl").

all() ->
    [initialize_handshake,
     protocol_version_negotiation,
     notifications_get_no_response,
     tools_are_listed_with_schemas,
     calling_a_tool_returns_text_and_structured_content,
     tool_errors_are_reported_in_the_result,
     unknown_method_is_a_jsonrpc_error,
     malformed_json_is_a_parse_error,
     batch_requests,
     resources_can_be_listed_and_read,
     prompts_can_be_listed_and_fetched,
     ask_tool_answers_a_question,
     every_tool_can_be_called].

init_per_suite(Config) ->
    bdd:feature("MCP protocol"),
    bdd:data_is_loaded(),
    Config.

end_per_suite(_Config) -> ok.

%%--------------------------------------------------------------------
%% Helpers
%%--------------------------------------------------------------------

request(Method, Params, Id) ->
    Message = br_json:encode(#{jsonrpc => <<"2.0">>, id => Id,
                               method => Method, params => Params}),
    case br_mcp_server:handle_message(Message) of
        {reply, Raw} ->
            {ok, Decoded} = br_json:decode(Raw),
            Decoded;
        noreply -> noreply
    end.

notify(Method, Params) ->
    Message = br_json:encode(#{jsonrpc => <<"2.0">>, method => Method, params => Params}),
    br_mcp_server:handle_message(Message).

result(Method, Params) ->
    #{<<"result">> := Result} = request(Method, Params, 1),
    Result.

%%--------------------------------------------------------------------
initialize_handshake(_Config) ->
    bdd:scenario("A client initialises the server"),
    bdd:given("the server is running", fun bdd:data_is_loaded/0),
    Response = bdd:'when'("the client sends initialize",
                          fun() ->
                                  request(<<"initialize">>,
                                          #{protocolVersion => <<"2025-06-18">>,
                                            capabilities => #{},
                                            clientInfo => #{name => <<"ct">>,
                                                            version => <<"1">>}},
                                          1)
                          end),
    bdd:then("the response should be a JSON-RPC result with server info",
             fun() ->
                     ?assertMatch(#{<<"jsonrpc">> := <<"2.0">>, <<"id">> := 1}, Response),
                     #{<<"result">> := R} = Response,
                     ?assertEqual(<<"2025-06-18">>, maps:get(<<"protocolVersion">>, R)),
                     ?assertMatch(#{<<"name">> := <<"brazilian-soccer">>},
                                  maps:get(<<"serverInfo">>, R))
             end),
    bdd:'and'("it should advertise tools, resources and prompts",
              fun() ->
                      #{<<"result">> := #{<<"capabilities">> := Caps}} = Response,
                      lists:foreach(fun(K) -> ?assert(maps:is_key(K, Caps)) end,
                                    [<<"tools">>, <<"resources">>, <<"prompts">>])
              end),
    bdd:'and'("it should include instructions for the model",
              fun() ->
                      #{<<"result">> := #{<<"instructions">> := Instructions}} = Response,
                      ?assert(byte_size(Instructions) > 100)
              end).

%%--------------------------------------------------------------------
protocol_version_negotiation(_Config) ->
    bdd:scenario("Protocol version negotiation"),
    bdd:given("the server is running", fun bdd:data_is_loaded/0),
    bdd:then("a supported version is echoed back",
             fun() ->
                     R = result(<<"initialize">>, #{protocolVersion => <<"2024-11-05">>}),
                     ?assertEqual(<<"2024-11-05">>, maps:get(<<"protocolVersion">>, R))
             end),
    bdd:'and'("an unknown version falls back to the latest supported one",
              fun() ->
                      R = result(<<"initialize">>, #{protocolVersion => <<"1999-01-01">>}),
                      ?assertEqual(<<"2025-06-18">>, maps:get(<<"protocolVersion">>, R))
              end).

%%--------------------------------------------------------------------
notifications_get_no_response(_Config) ->
    bdd:scenario("Notifications are not answered"),
    bdd:given("the server is running", fun bdd:data_is_loaded/0),
    bdd:then("notifications/initialized produces no reply",
             fun() -> ?assertEqual(noreply, notify(<<"notifications/initialized">>, #{})) end),
    bdd:'and'("an unknown notification is silently ignored",
              fun() -> ?assertEqual(noreply, notify(<<"notifications/whatever">>, #{})) end).

%%--------------------------------------------------------------------
tools_are_listed_with_schemas(_Config) ->
    bdd:scenario("The client lists the tools"),
    bdd:given("the server is running", fun bdd:data_is_loaded/0),
    Tools = bdd:'when'("the client sends tools/list",
                       fun() -> maps:get(<<"tools">>, result(<<"tools/list">>, #{})) end),
    bdd:then("every tool should have a name, description and input schema",
             fun() ->
                     ?assert(length(Tools) >= 15),
                     lists:foreach(
                       fun(T) ->
                               ?assertMatch(#{<<"name">> := <<_/binary>>}, T),
                               ?assertMatch(#{<<"description">> := <<_/binary>>}, T),
                               Schema = maps:get(<<"inputSchema">>, T),
                               ?assertEqual(<<"object">>, maps:get(<<"type">>, Schema)),
                               ?assert(maps:is_key(<<"properties">>, Schema))
                       end, Tools)
             end),
    bdd:'and'("the tool names should be unique",
              fun() ->
                      Names = [maps:get(<<"name">>, T) || T <- Tools],
                      ?assertEqual(lists:usort(Names), lists:sort(Names))
              end).

%%--------------------------------------------------------------------
calling_a_tool_returns_text_and_structured_content(_Config) ->
    bdd:scenario("The client calls a tool"),
    bdd:given("the server is running", fun bdd:data_is_loaded/0),
    Result = bdd:'when'("the client calls standings for 2019",
                        fun() ->
                                result(<<"tools/call">>,
                                       #{name => <<"standings">>,
                                         arguments => #{season => 2019, limit => 5}})
                        end),
    bdd:then("the result should contain a text block",
             fun() ->
                     [#{<<"type">> := Type, <<"text">> := Text}] =
                         maps:get(<<"content">>, Result),
                     ?assertEqual(<<"text">>, Type),
                     ?assertNotEqual(nomatch, binary:match(Text, <<"Flamengo">>))
             end),
    bdd:'and'("it should also contain the structured data",
              fun() ->
                      Structured = maps:get(<<"structuredContent">>, Result),
                      ?assertEqual(<<"Flamengo">>, maps:get(<<"champion">>, Structured)),
                      ?assertEqual(5, length(maps:get(<<"table">>, Structured)))
              end),
    bdd:'and'("isError should be false",
              fun() -> ?assertEqual(false, maps:get(<<"isError">>, Result)) end).

%%--------------------------------------------------------------------
tool_errors_are_reported_in_the_result(_Config) ->
    bdd:scenario("A tool level error is reported to the model, not as a protocol error"),
    bdd:given("the server is running", fun bdd:data_is_loaded/0),
    Response = bdd:'when'("the client asks about an unknown club",
                          fun() ->
                                  request(<<"tools/call">>,
                                          #{name => <<"team_stats">>,
                                            arguments => #{team => <<"Barcelona FC 1899">>}},
                                          7)
                          end),
    bdd:then("the response should be a successful JSON-RPC result",
             fun() -> ?assert(maps:is_key(<<"result">>, Response)) end),
    bdd:'and'("with isError set and a readable message",
              fun() ->
                      Result = maps:get(<<"result">>, Response),
                      ?assertEqual(true, maps:get(<<"isError">>, Result)),
                      [#{<<"text">> := Text}] = maps:get(<<"content">>, Result),
                      ?assertNotEqual(nomatch, binary:match(Text, <<"unknown team">>))
              end),
    bdd:'and'("an unknown tool is reported the same way",
              fun() ->
                      R = result(<<"tools/call">>, #{name => <<"no_such_tool">>,
                                                     arguments => #{}}),
                      ?assertEqual(true, maps:get(<<"isError">>, R))
              end).

%%--------------------------------------------------------------------
unknown_method_is_a_jsonrpc_error(_Config) ->
    bdd:scenario("An unknown method gets a JSON-RPC error"),
    bdd:given("the server is running", fun bdd:data_is_loaded/0),
    Response = bdd:'when'("the client calls a method that does not exist",
                          fun() -> request(<<"does/notexist">>, #{}, 42) end),
    bdd:then("error -32601 should come back with the same id",
             fun() ->
                     ?assertEqual(42, maps:get(<<"id">>, Response)),
                     #{<<"error">> := #{<<"code">> := Code}} = Response,
                     ?assertEqual(-32601, Code)
             end).

%%--------------------------------------------------------------------
malformed_json_is_a_parse_error(_Config) ->
    bdd:scenario("Malformed input gets a parse error"),
    bdd:given("the server is running", fun bdd:data_is_loaded/0),
    bdd:then("error -32700 is returned",
             fun() ->
                     {reply, Raw} = br_mcp_server:handle_message(<<"{oops">>),
                     {ok, #{<<"error">> := #{<<"code">> := Code}, <<"id">> := Id}} =
                         br_json:decode(Raw),
                     ?assertEqual(-32700, Code),
                     ?assertEqual(null, Id)
             end).

%%--------------------------------------------------------------------
batch_requests(_Config) ->
    bdd:scenario("A batch of requests gets a batch of responses"),
    bdd:given("the server is running", fun bdd:data_is_loaded/0),
    Responses = bdd:'when'("two requests and one notification are sent together",
                           fun() ->
                                   Batch = br_json:encode(
                                             [#{jsonrpc => <<"2.0">>, id => 1,
                                                method => <<"ping">>},
                                              #{jsonrpc => <<"2.0">>,
                                                method => <<"notifications/initialized">>},
                                              #{jsonrpc => <<"2.0">>, id => 2,
                                                method => <<"tools/list">>}]),
                                   {reply, Raw} = br_mcp_server:handle_message(Batch),
                                   {ok, Decoded} = br_json:decode(Raw),
                                   Decoded
                           end),
    bdd:then("only the two requests should be answered",
             fun() ->
                     ?assertEqual(2, length(Responses)),
                     ?assertEqual([1, 2], lists:sort([maps:get(<<"id">>, R)
                                                      || R <- Responses]))
             end).

%%--------------------------------------------------------------------
resources_can_be_listed_and_read(_Config) ->
    bdd:scenario("Resources expose the data sets to the client"),
    bdd:given("the server is running", fun bdd:data_is_loaded/0),
    Resources = bdd:'when'("the client lists the resources",
                           fun() ->
                                   maps:get(<<"resources">>, result(<<"resources/list">>, #{}))
                           end),
    bdd:then("each resource should have a uri and a mime type",
             fun() ->
                     ?assert(length(Resources) >= 4),
                     lists:foreach(
                       fun(R) ->
                               ?assertMatch(#{<<"uri">> := <<"soccer://", _/binary>>}, R),
                               ?assert(maps:is_key(<<"mimeType">>, R))
                       end, Resources)
             end),
    bdd:'and'("reading a JSON resource should return valid JSON",
              fun() ->
                      R = result(<<"resources/read">>, #{uri => <<"soccer://competitions">>}),
                      [#{<<"text">> := Text}] = maps:get(<<"contents">>, R),
                      {ok, Parsed} = br_json:decode(Text),
                      ?assert(maps:is_key(<<"competitions">>, Parsed))
              end),
    bdd:'and'("an unknown uri is an error",
              fun() ->
                      Response = request(<<"resources/read">>,
                                         #{uri => <<"soccer://nope">>}, 3),
                      ?assert(maps:is_key(<<"error">>, Response))
              end).

%%--------------------------------------------------------------------
prompts_can_be_listed_and_fetched(_Config) ->
    bdd:scenario("Prompts help the model use the server"),
    bdd:given("the server is running", fun bdd:data_is_loaded/0),
    Prompts = bdd:'when'("the client lists the prompts",
                         fun() -> maps:get(<<"prompts">>, result(<<"prompts/list">>, #{})) end),
    bdd:then("the prompts should be described",
             fun() ->
                     ?assert(length(Prompts) >= 2),
                     lists:foreach(fun(P) ->
                                           ?assert(maps:is_key(<<"name">>, P)),
                                           ?assert(maps:is_key(<<"arguments">>, P))
                                   end, Prompts)
             end),
    bdd:'and'("fetching one fills in the arguments",
              fun() ->
                      R = result(<<"prompts/get">>,
                                 #{name => <<"scouting_report">>,
                                   arguments => #{<<"team">> => <<"Santos">>}}),
                      [#{<<"content">> := #{<<"text">> := Text}}] =
                          maps:get(<<"messages">>, R),
                      ?assertNotEqual(nomatch, binary:match(Text, <<"Santos">>))
              end).

%%--------------------------------------------------------------------
ask_tool_answers_a_question(_Config) ->
    bdd:scenario("The ask tool answers a natural language question"),
    bdd:given("the server is running", fun bdd:data_is_loaded/0),
    Result = bdd:'when'("the client asks who won the 2019 Brasileirao",
                        fun() ->
                                result(<<"tools/call">>,
                                       #{name => <<"ask">>,
                                         arguments =>
                                             #{question =>
                                                   <<"Who won the 2019 Brasileirao?">>}})
                        end),
    bdd:then("the answer should name Flamengo",
             fun() ->
                     [#{<<"text">> := Text}] = maps:get(<<"content">>, Result),
                     ?assertNotEqual(nomatch, binary:match(Text, <<"Flamengo">>))
             end),
    bdd:'and'("the structured result should show which tool was used",
              fun() ->
                      Structured = maps:get(<<"structuredContent">>, Result),
                      ?assertEqual(<<"standings">>, maps:get(<<"tool">>, Structured))
              end).

%%--------------------------------------------------------------------
every_tool_can_be_called(_Config) ->
    bdd:scenario("Every advertised tool answers a representative call"),
    bdd:given("the server is running", fun bdd:data_is_loaded/0),
    Calls = [{<<"ask">>, #{question => <<"What data sets are loaded?">>}},
             {<<"search_matches">>, #{team => <<"Santos">>, limit => 3}},
             {<<"head_to_head">>, #{team_a => <<"Santos">>, team_b => <<"Palmeiras">>}},
             {<<"team_stats">>, #{team => <<"Santos">>}},
             {<<"team_profile">>, #{team => <<"Santos">>}},
             {<<"standings">>, #{season => 2019}},
             {<<"team_rankings">>, #{season => 2019, competition => <<"serie a">>}},
             {<<"competition_stats">>, #{competition => <<"serie a">>}},
             {<<"compare_seasons">>, #{season_a => 2018, season_b => 2019}},
             {<<"biggest_wins">>, #{limit => 3}},
             {<<"search_players">>, #{nationality => <<"Brazil">>, limit => 3}},
             {<<"player_profile">>, #{name => <<"Neymar">>}},
             {<<"club_squad">>, #{club => <<"Gremio">>}},
             {<<"players_by_club">>, #{nationality => <<"Brazil">>, limit => 5}},
             {<<"derbies">>, #{season => 2019}},
             {<<"list_teams">>, #{limit => 5}},
             {<<"list_competitions">>, #{}},
             {<<"dataset_summary">>, #{}},
             {<<"graph_neighbors">>, #{node => <<"team:santos">>, limit => 5}},
             {<<"graph_path">>, #{from => <<"team:santos">>, to => <<"season:2019">>}}],
    bdd:then("each call returns text without an error",
             fun() ->
                     ?assertEqual(lists:sort(br_mcp_tools:names()),
                                  lists:sort([N || {N, _} <- Calls])),
                     lists:foreach(
                       fun({Name, Args}) ->
                               R = result(<<"tools/call">>, #{name => Name,
                                                              arguments => Args}),
                               [#{<<"text">> := Text}] = maps:get(<<"content">>, R),
                               ct:log("~ts -> ~ts", [Name, string:slice(Text, 0, 120)]),
                               ?assertEqual({Name, false},
                                            {Name, maps:get(<<"isError">>, R)}),
                               ?assert(byte_size(Text) > 10)
                       end, Calls)
             end).
