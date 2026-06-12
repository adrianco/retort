%%% ===================================================================
%%% Brazilian Soccer MCP Server - JSON-RPC / MCP protocol layer
%%%
%%% Context: This is the public interface of the server. It speaks the
%%% Model Context Protocol over JSON-RPC 2.0. `handle/1' takes a single
%%% encoded JSON-RPC request and returns the encoded JSON-RPC response,
%%% which is exactly what the stdio transport (`bsoccer_stdio') and the
%%% acceptance tests drive.
%%%
%%% Supported methods:
%%%   initialize                 - MCP handshake
%%%   tools/list                 - advertise the soccer query tools
%%%   tools/call                 - invoke a tool by name with arguments
%%%   ping                       - liveness
%%% Each tool dispatches into `bsoccer_query' for the data and
%%% `bsoccer_format' for the human-readable text. A tool result carries
%%% both `content' (text) and `structuredContent' (the machine-readable
%%% map), per the MCP tool-result shape.
%%% ===================================================================
-module(bsoccer_mcp).

-export([handle/1, tool_specs/0]).

-define(PROTOCOL_VERSION, <<"2024-11-05">>).
-define(SERVER_NAME, <<"brazilian-soccer-mcp">>).
-define(SERVER_VERSION, <<"1.0.0">>).

%% Decode a JSON-RPC request, dispatch it, and encode the response.
-spec handle(iodata()) -> binary().
handle(RequestJson) ->
    try json:decode(iolist_to_binary(RequestJson)) of
        Request when is_map(Request) ->
            iolist_to_binary(json:encode(dispatch(Request)));
        _ ->
            iolist_to_binary(json:encode(error_response(null, -32600, <<"Invalid Request">>)))
    catch
        _:_ ->
            iolist_to_binary(json:encode(error_response(null, -32700, <<"Parse error">>)))
    end.

%%% -------------------------------------------------------------------
%%% Dispatch
%%% -------------------------------------------------------------------

dispatch(Request) ->
    Id = maps:get(<<"id">>, Request, null),
    Method = maps:get(<<"method">>, Request, <<>>),
    Params = maps:get(<<"params">>, Request, #{}),
    case Method of
        <<"initialize">> -> ok_response(Id, initialize_result());
        <<"ping">> -> ok_response(Id, #{});
        <<"tools/list">> -> ok_response(Id, #{<<"tools">> => tool_specs()});
        <<"tools/call">> -> handle_tool_call(Id, Params);
        <<"notifications/initialized">> -> ok_response(Id, #{});
        _ -> error_response(Id, -32601, <<"Method not found: ", Method/binary>>)
    end.

initialize_result() ->
    #{<<"protocolVersion">> => ?PROTOCOL_VERSION,
      <<"capabilities">> => #{<<"tools">> => #{}},
      <<"serverInfo">> => #{<<"name">> => ?SERVER_NAME,
                            <<"version">> => ?SERVER_VERSION},
      <<"instructions">> =>
          <<"Query Brazilian soccer matches, teams, players, competitions "
            "and statistics from the bundled Kaggle datasets.">>}.

%%% -------------------------------------------------------------------
%%% tools/call
%%% -------------------------------------------------------------------

handle_tool_call(Id, Params) ->
    Name = maps:get(<<"name">>, Params, <<>>),
    Args = case maps:get(<<"arguments">>, Params, #{}) of
               A when is_map(A) -> A;
               _ -> #{}
           end,
    case run_tool(Name, Args) of
        {ok, Structured} ->
            Text = bsoccer_format:render(Name, Structured),
            ok_response(Id, tool_result(Text, Structured, false));
        {error, Reason} ->
            ok_response(Id, tool_result(Reason, undefined, true))
    end.

run_tool(Name, Args) ->
    try
        case Name of
            <<"find_matches">> -> {ok, bsoccer_query:find_matches(Args)};
            <<"head_to_head">> -> {ok, bsoccer_query:head_to_head(Args)};
            <<"team_statistics">> -> {ok, bsoccer_query:team_statistics(Args)};
            <<"search_players">> -> {ok, bsoccer_query:search_players(Args)};
            <<"competition_standings">> -> {ok, bsoccer_query:competition_standings(Args)};
            <<"aggregate_statistics">> -> {ok, bsoccer_query:aggregate_statistics(Args)};
            <<"list_competitions">> -> {ok, bsoccer_query:list_competitions(Args)};
            _ -> {error, <<"Unknown tool: ", Name/binary>>}
        end
    catch
        Class:CatchReason:Stack ->
            error_logger:error_msg("bsoccer tool ~s failed: ~p:~p~n~p~n",
                                   [Name, Class, CatchReason, Stack]),
            {error, <<"Tool execution error">>}
    end.

tool_result(Text, undefined, IsError) ->
    #{<<"content">> => [#{<<"type">> => <<"text">>, <<"text">> => to_text(Text)}],
      <<"isError">> => IsError};
tool_result(Text, Structured, IsError) ->
    #{<<"content">> => [#{<<"type">> => <<"text">>, <<"text">> => to_text(Text)}],
      <<"structuredContent">> => Structured,
      <<"isError">> => IsError}.

to_text(B) when is_binary(B) -> B;
to_text(L) -> unicode:characters_to_binary(L).

%%% -------------------------------------------------------------------
%%% JSON-RPC envelopes
%%% -------------------------------------------------------------------

ok_response(Id, Result) ->
    #{<<"jsonrpc">> => <<"2.0">>, <<"id">> => Id, <<"result">> => Result}.

error_response(Id, Code, Message) ->
    #{<<"jsonrpc">> => <<"2.0">>, <<"id">> => Id,
      <<"error">> => #{<<"code">> => Code, <<"message">> => Message}}.

%%% -------------------------------------------------------------------
%%% Tool catalogue (advertised via tools/list)
%%% -------------------------------------------------------------------

tool_specs() ->
    [tool(<<"find_matches">>,
          <<"Find soccer matches by team, opponent, competition, season or "
            "date range. Returns the most recent matches first.">>,
          #{<<"team">> => str(<<"Team name, e.g. \"Flamengo\" (matches "
                               "\"Flamengo-RJ\" too)">>),
            <<"opponent">> => str(<<"Restrict to matches against this opponent">>),
            <<"competition">> => str(<<"Brasileirão, Copa do Brasil or Libertadores"/utf8>>),
            <<"season">> => int(<<"Season year, e.g. 2019">>),
            <<"start_date">> => str(<<"Earliest match date (YYYY-MM-DD)">>),
            <<"end_date">> => str(<<"Latest match date (YYYY-MM-DD)">>),
            <<"limit">> => int(<<"Maximum matches to return">>)},
          []),
     tool(<<"head_to_head">>,
          <<"Head-to-head record between two teams: wins, draws and the "
            "list of meetings.">>,
          #{<<"team1">> => str(<<"First team">>),
            <<"team2">> => str(<<"Second team">>),
            <<"competition">> => str(<<"Optional competition filter">>),
            <<"season">> => int(<<"Optional season filter">>),
            <<"limit">> => int(<<"Maximum meetings to list">>)},
          [<<"team1">>, <<"team2">>]),
     tool(<<"team_statistics">>,
          <<"Win/draw/loss record, goals and points for a team, optionally "
            "filtered by season, competition and venue (home/away/all).">>,
          #{<<"team">> => str(<<"Team name">>),
            <<"season">> => int(<<"Optional season year">>),
            <<"competition">> => str(<<"Optional competition">>),
            <<"venue">> => str(<<"home, away or all (default all)">>)},
          [<<"team">>]),
     tool(<<"search_players">>,
          <<"Search FIFA players by name, nationality, club or position; "
            "sortable by rating, potential, age or name.">>,
          #{<<"name">> => str(<<"Substring of the player name">>),
            <<"nationality">> => str(<<"Nationality, e.g. \"Brazil\"">>),
            <<"club">> => str(<<"Club name substring">>),
            <<"position">> => str(<<"Position, e.g. \"ST\", \"GK\"">>),
            <<"min_overall">> => int(<<"Minimum overall rating">>),
            <<"sort_by">> => str(<<"overall | potential | age | name">>),
            <<"limit">> => int(<<"Maximum players to return">>)},
          []),
     tool(<<"competition_standings">>,
          <<"League standings for a competition and season, calculated from "
            "match results (3 points per win).">>,
          #{<<"competition">> => str(<<"Competition, e.g. \"Brasileirão\""/utf8>>),
            <<"season">> => int(<<"Season year, e.g. 2019">>),
            <<"limit">> => int(<<"Maximum table rows">>)},
          [<<"competition">>, <<"season">>]),
     tool(<<"aggregate_statistics">>,
          <<"Aggregate statistics over matches: average goals per match, "
            "home/away win rates and the biggest victories.">>,
          #{<<"competition">> => str(<<"Optional competition filter">>),
            <<"season">> => int(<<"Optional season filter">>)},
          []),
     tool(<<"list_competitions">>,
          <<"List the loaded competitions with match counts and the seasons "
            "covered.">>,
          #{},
          [])].

tool(Name, Description, Properties, Required) ->
    #{<<"name">> => Name,
      <<"description">> => Description,
      <<"inputSchema">> =>
          #{<<"type">> => <<"object">>,
            <<"properties">> => Properties,
            <<"required">> => Required}}.

str(Desc) -> #{<<"type">> => <<"string">>, <<"description">> => Desc}.
int(Desc) -> #{<<"type">> => <<"integer">>, <<"description">> => Desc}.
