%%% =====================================================================
%%% bsoccer_mcp — Model Context Protocol (JSON-RPC 2.0) request handling.
%%%
%%% This module is the protocol brain of the server. It is transport-agnostic:
%%% `handle_message/1` takes a decoded JSON-RPC object (a map) and returns
%%% either `{reply, ResponseMap}` for requests or `noreply` for notifications.
%%% bsoccer_cli wires it to a stdio read/write loop, which is the standard MCP
%%% transport, but the same function is exercised directly by the test suite.
%%%
%%% Implemented MCP surface:
%%%   initialize                -> protocol handshake + capabilities
%%%   notifications/initialized -> acknowledged (no reply)
%%%   ping                      -> {}
%%%   tools/list                -> the soccer query tool catalogue
%%%   tools/call                -> dispatch to bsoccer_query, wrap as content
%%%
%%% Tool results follow the MCP shape `{content:[{type:"text",text:...}]}` so
%%% the answer text drops straight into an LLM conversation; on bad arguments
%%% the result carries `isError: true` rather than a transport-level error.
%%% =====================================================================
-module(bsoccer_mcp).

-export([handle_message/1, tools/0, call_tool/2, server_info/0]).

-define(PROTOCOL_VERSION, <<"2024-11-05">>).

%% =====================================================================
%% Message dispatch
%% =====================================================================

-spec handle_message(map()) -> {reply, map()} | noreply.
handle_message(#{<<"method">> := Method} = Msg) ->
    Id = maps:get(<<"id">>, Msg, undefined),
    Params = maps:get(<<"params">>, Msg, #{}),
    case {is_request(Id), dispatch(Method, Params)} of
        {true, {ok, Result}} ->
            {reply, success(Id, Result)};
        {true, {error, Code, Message}} ->
            {reply, error_response(Id, Code, Message)};
        {false, _} ->
            %% Notification: never reply.
            noreply
    end;
handle_message(_Other) ->
    %% Malformed object with no method — ignore per JSON-RPC notification rules.
    noreply.

is_request(undefined) -> false;
is_request(_) -> true.

dispatch(<<"initialize">>, _Params) ->
    {ok, #{<<"protocolVersion">> => ?PROTOCOL_VERSION,
           <<"capabilities">> => #{<<"tools">> => #{<<"listChanged">> => false}},
           <<"serverInfo">> => server_info(),
           <<"instructions">> =>
               <<"Query Brazilian soccer match, team, competition and FIFA "
                 "player data. Use search_matches/head_to_head/team_record/"
                 "standings/match_statistics for results, search_players for "
                 "the FIFA database, and data_summary for an overview.">>}};
dispatch(<<"notifications/initialized">>, _Params) ->
    {ok, #{}};
dispatch(<<"ping">>, _Params) ->
    {ok, #{}};
dispatch(<<"tools/list">>, _Params) ->
    {ok, #{<<"tools">> => tools()}};
dispatch(<<"tools/call">>, Params) ->
    Name = maps:get(<<"name">>, Params, undefined),
    Args = maps:get(<<"arguments">>, Params, #{}),
    case Name of
        undefined ->
            {error, -32602, <<"missing tool name">>};
        _ ->
            {ok, call_tool(Name, Args)}
    end;
dispatch(Method, _Params) ->
    {error, -32601, <<"method not found: ", Method/binary>>}.

server_info() ->
    #{<<"name">> => <<"brazilian-soccer-mcp">>,
      <<"version">> => <<"1.0.0">>}.

%% =====================================================================
%% Tool dispatch
%% =====================================================================

%% Run a named tool, translating its `#{text, data}` answer into an MCP
%% content result. Missing required arguments become a tool error (isError)
%% rather than a protocol error so the LLM can recover conversationally.
-spec call_tool(binary(), map()) -> map().
call_tool(Name, Args) ->
    try
        Result = run_tool(Name, Args),
        Text = maps:get(text, Result),
        Data = maps:get(data, Result),
        #{<<"content">> => [text_content(Text)],
          <<"structuredContent">> => #{<<"result">> => Data}}
    catch
        throw:{missing_argument, Key} ->
            tool_error(fmt("missing required argument: ~ts", [Key]));
        throw:{unknown_tool, N} ->
            tool_error(fmt("unknown tool: ~ts", [N]));
        Class:Reason:Stack ->
            io:format(standard_error, "tool error ~p:~p~n~p~n",
                      [Class, Reason, Stack]),
            tool_error(fmt("internal error running ~ts", [Name]))
    end.

run_tool(<<"search_matches">>, Args) -> bsoccer_query:search_matches(Args);
run_tool(<<"head_to_head">>, Args) -> bsoccer_query:head_to_head(Args);
run_tool(<<"team_record">>, Args) -> bsoccer_query:team_record(Args);
run_tool(<<"standings">>, Args) -> bsoccer_query:standings(Args);
run_tool(<<"search_players">>, Args) -> bsoccer_query:search_players(Args);
run_tool(<<"match_statistics">>, Args) -> bsoccer_query:match_stats(Args);
run_tool(<<"data_summary">>, Args) -> bsoccer_query:data_summary(Args);
run_tool(Name, _Args) -> throw({unknown_tool, Name}).

text_content(Text) ->
    #{<<"type">> => <<"text">>, <<"text">> => Text}.

tool_error(Msg) ->
    #{<<"content">> => [text_content(Msg)], <<"isError">> => true}.

%% =====================================================================
%% JSON-RPC envelopes
%% =====================================================================

success(Id, Result) ->
    #{<<"jsonrpc">> => <<"2.0">>, <<"id">> => Id, <<"result">> => Result}.

error_response(Id, Code, Message) ->
    #{<<"jsonrpc">> => <<"2.0">>, <<"id">> => Id,
      <<"error">> => #{<<"code">> => Code, <<"message">> => Message}}.

%% =====================================================================
%% Tool catalogue (MCP inputSchema = JSON Schema)
%% =====================================================================

-spec tools() -> [map()].
tools() ->
    [#{<<"name">> => <<"search_matches">>,
       <<"description">> =>
           <<"Search matches across Brasileirão, Copa do Brasil and Copa "
             "Libertadores by team, opponent, competition, season, season "
             "range, date range and venue. Returns matches with scores and a "
             "head-to-head summary when both team and opponent are given."/utf8>>,
       <<"inputSchema">> => obj(
          #{<<"team">> => str("Team name (state suffixes/accents optional, e.g. 'Flamengo')"),
            <<"opponent">> => str("Opponent team name to restrict to a specific fixture"),
            <<"competition">> => str("Competition filter, e.g. 'Brasileirão', 'Copa do Brasil', 'Libertadores'"),
            <<"season">> => int("Exact season/year"),
            <<"season_from">> => int("Earliest season (inclusive)"),
            <<"season_to">> => int("Latest season (inclusive)"),
            <<"date_from">> => str("Earliest match date (YYYY-MM-DD)"),
            <<"date_to">> => str("Latest match date (YYYY-MM-DD)"),
            <<"venue">> => enum("Restrict team to home/away/either", [<<"home">>, <<"away">>, <<"either">>]),
            <<"limit">> => int("Maximum matches to return (default 30)")},
          [])},

     #{<<"name">> => <<"head_to_head">>,
       <<"description">> =>
           <<"Compute the head-to-head record between two teams across all "
             "competitions in the dataset: wins, draws, goals and recent "
             "meetings.">>,
       <<"inputSchema">> => obj(
          #{<<"team1">> => str("First team"),
            <<"team2">> => str("Second team"),
            <<"competition">> => str("Optional competition filter")},
          [<<"team1">>, <<"team2">>])},

     #{<<"name">> => <<"team_record">>,
       <<"description">> =>
           <<"Win/draw/loss record, goals for/against and win rate for a "
             "team, optionally scoped to a season, competition and home/away "
             "venue.">>,
       <<"inputSchema">> => obj(
          #{<<"team">> => str("Team name"),
            <<"season">> => int("Season/year filter"),
            <<"competition">> => str("Competition filter"),
            <<"venue">> => enum("home/away/either (default either)", [<<"home">>, <<"away">>, <<"either">>])},
          [<<"team">>])},

     #{<<"name">> => <<"standings">>,
       <<"description">> =>
           <<"Compute a league table for a competition and season directly "
             "from match results (points, W/D/L, goals, goal difference), "
             "ranked with the champion first.">>,
       <<"inputSchema">> => obj(
          #{<<"season">> => int("Season/year (required)"),
            <<"competition">> => str("Competition (default 'Brasileirão Série A')"),
            <<"limit">> => int("Number of table rows to return (default 20)")},
          [<<"season">>])},

     #{<<"name">> => <<"search_players">>,
       <<"description">> =>
           <<"Search the FIFA player database by name, nationality, club, "
             "position and minimum overall rating; sort by overall or "
             "potential. Great for 'Brazilian players' or 'players at "
             "Flamengo' style questions.">>,
       <<"inputSchema">> => obj(
          #{<<"name">> => str("Player name substring"),
            <<"nationality">> => str("Nationality, e.g. 'Brazil'"),
            <<"club">> => str("Club name substring, e.g. 'Flamengo'"),
            <<"position">> => str("Position code, e.g. 'ST', 'GK', 'CB'"),
            <<"min_overall">> => int("Minimum FIFA overall rating"),
            <<"sort">> => enum("Sort field", [<<"overall">>, <<"potential">>]),
            <<"limit">> => int("Maximum players to return (default 15)")},
          [])},

     #{<<"name">> => <<"match_statistics">>,
       <<"description">> =>
           <<"Aggregate statistics over a filtered set of matches: total and "
             "average goals per match, home/draw/away win rates, and the "
             "biggest victories by margin.">>,
       <<"inputSchema">> => obj(
          #{<<"team">> => str("Restrict to matches involving this team"),
            <<"competition">> => str("Competition filter"),
            <<"season">> => int("Exact season"),
            <<"season_from">> => int("Earliest season (inclusive)"),
            <<"season_to">> => int("Latest season (inclusive)")},
          [])},

     #{<<"name">> => <<"data_summary">>,
       <<"description">> =>
           <<"Overview of the loaded knowledge graph: total matches, FIFA "
             "players, and a breakdown of matches per competition.">>,
       <<"inputSchema">> => obj(#{}, [])}
    ].

%% --- JSON Schema builders -------------------------------------------------

obj(Props, Required) ->
    Base = #{<<"type">> => <<"object">>, <<"properties">> => Props},
    case Required of
        [] -> Base;
        _ -> Base#{<<"required">> => Required}
    end.

str(Desc) -> #{<<"type">> => <<"string">>, <<"description">> => bin(Desc)}.
int(Desc) -> #{<<"type">> => <<"integer">>, <<"description">> => bin(Desc)}.
enum(Desc, Values) ->
    #{<<"type">> => <<"string">>, <<"description">> => bin(Desc),
      <<"enum">> => Values}.

bin(L) when is_list(L) -> unicode:characters_to_binary(L);
bin(B) when is_binary(B) -> B.

fmt(Format, Args) -> unicode:characters_to_binary(io_lib:format(Format, Args)).
