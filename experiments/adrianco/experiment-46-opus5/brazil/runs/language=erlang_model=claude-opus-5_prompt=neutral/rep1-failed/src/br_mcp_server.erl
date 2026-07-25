%%%-------------------------------------------------------------------
%%% @doc MCP (Model Context Protocol) JSON-RPC 2.0 server core.
%%%
%%% Transport independent: {@link handle_message/1} takes one raw
%%% JSON-RPC message (or batch) and returns the raw reply, which makes
%%% the whole protocol layer directly testable.  {@link br_mcp_stdio}
%%% wires it to stdin/stdout, the transport MCP clients use by default.
%%%
%%% Implemented methods: `initialize', `ping', `tools/list',
%%% `tools/call', `resources/list', `resources/read',
%%% `resources/templates/list', `prompts/list', `prompts/get' and the
%%% `notifications/*' no-ops.
%%% @end
%%%-------------------------------------------------------------------
-module(br_mcp_server).

-export([handle_message/1,
         handle_request/1,
         server_info/0,
         capabilities/0,
         protocol_versions/0,
         resources/0,
         prompts/0]).

-define(LATEST_PROTOCOL, <<"2025-06-18">>).
-define(PARSE_ERROR, -32700).
-define(INVALID_REQUEST, -32600).
-define(METHOD_NOT_FOUND, -32601).
-define(INVALID_PARAMS, -32602).
-define(INTERNAL_ERROR, -32603).

%%--------------------------------------------------------------------
%% @doc Handle one raw JSON-RPC message.
-spec handle_message(binary()) -> {reply, binary()} | noreply.
handle_message(Raw) ->
    case br_json:decode(Raw) of
        {error, _} ->
            {reply, br_json:encode(error_response(null, ?PARSE_ERROR,
                                                  <<"invalid JSON">>, null))};
        {ok, Batch} when is_list(Batch) ->
            Replies = [R || Message <- Batch,
                            {reply, R} <- [dispatch_or_noreply(Message)]],
            case Replies of
                [] -> noreply;
                _ -> {reply, br_json:encode(Replies)}
            end;
        {ok, Message} when is_map(Message) ->
            case dispatch_or_noreply(Message) of
                {reply, Response} -> {reply, br_json:encode(Response)};
                noreply -> noreply
            end;
        {ok, _} ->
            {reply, br_json:encode(error_response(null, ?INVALID_REQUEST,
                                                  <<"expected an object">>, null))}
    end.

dispatch_or_noreply(Message) when is_map(Message) ->
    Id = maps:get(<<"id">>, Message, undefined),
    Method = maps:get(<<"method">>, Message, undefined),
    Params = params(maps:get(<<"params">>, Message, #{})),
    case {Id, Method} of
        {_, undefined} when Id =/= undefined ->
            {reply, error_response(Id, ?INVALID_REQUEST, <<"missing method">>, null)};
        {undefined, _} ->
            %% Notification: no response, ever.
            _ = handle(Method, Params),
            noreply;
        _ ->
            case handle(Method, Params) of
                {ok, Result} -> {reply, result_response(Id, Result)};
                {error, Code, Reason, Data} ->
                    {reply, error_response(Id, Code, Reason, Data)}
            end
    end;
dispatch_or_noreply(_) ->
    {reply, error_response(null, ?INVALID_REQUEST, <<"expected an object">>, null)}.

params(P) when is_map(P) -> P;
params(_) -> #{}.

%%--------------------------------------------------------------------
%% @doc Handle a decoded request; exported for tests.
-spec handle_request(map()) -> {reply, map()} | noreply.
handle_request(Message) -> dispatch_or_noreply(Message).

%%====================================================================
%% Methods
%%====================================================================

handle(<<"initialize">>, Params) ->
    Requested = maps:get(<<"protocolVersion">>, Params, ?LATEST_PROTOCOL),
    Version = case lists:member(Requested, protocol_versions()) of
                  true -> Requested;
                  false -> ?LATEST_PROTOCOL
              end,
    {ok, #{protocolVersion => Version,
           capabilities => capabilities(),
           serverInfo => server_info(),
           instructions => instructions()}};

handle(<<"ping">>, _Params) ->
    {ok, #{}};

handle(<<"tools/list">>, _Params) ->
    {ok, #{tools => br_mcp_tools:list()}};

handle(<<"tools/call">>, Params) ->
    case maps:get(<<"name">>, Params, undefined) of
        undefined ->
            {error, ?INVALID_PARAMS, <<"tools/call requires a name">>, null};
        Name ->
            Args = case maps:get(<<"arguments">>, Params, #{}) of
                       A when is_map(A) -> A;
                       _ -> #{}
                   end,
            {ok, call_tool(Name, Args)}
    end;

handle(<<"resources/list">>, _Params) ->
    {ok, #{resources => [maps:without([read], R) || R <- resources()]}};

handle(<<"resources/templates/list">>, _Params) ->
    {ok, #{resourceTemplates => []}};

handle(<<"resources/read">>, Params) ->
    Uri = maps:get(<<"uri">>, Params, undefined),
    case [R || #{uri := U} = R <- resources(), U =:= Uri] of
        [#{read := Read, mimeType := Mime} | _] ->
            {ok, #{contents => [#{uri => Uri, mimeType => Mime, text => Read()}]}};
        [] ->
            {error, ?INVALID_PARAMS, <<"unknown resource">>,
             #{available => [U || #{uri := U} <- resources()]}}
    end;

handle(<<"prompts/list">>, _Params) ->
    {ok, #{prompts => [maps:without([build], P) || P <- prompts()]}};

handle(<<"prompts/get">>, Params) ->
    Name = maps:get(<<"name">>, Params, undefined),
    Args = maps:get(<<"arguments">>, Params, #{}),
    case [P || #{name := N} = P <- prompts(), N =:= Name] of
        [#{build := Build, description := Description} | _] ->
            {ok, #{description => Description,
                   messages => [#{role => <<"user">>,
                                  content => #{type => <<"text">>,
                                               text => Build(Args)}}]}};
        [] ->
            {error, ?INVALID_PARAMS, <<"unknown prompt">>, null}
    end;

handle(<<"logging/setLevel">>, _Params) ->
    {ok, #{}};

handle(<<"notifications/initialized">>, _Params) -> {ok, #{}};
handle(<<"notifications/cancelled">>, _Params) -> {ok, #{}};
handle(<<"notifications/", _/binary>>, _Params) -> {ok, #{}};

handle(Method, _Params) ->
    {error, ?METHOD_NOT_FOUND,
     <<"method not found: ", (br_text:to_binary(Method))/binary>>, null}.

%%--------------------------------------------------------------------
%% Tool invocation: tool level failures are reported inside the result
%% (isError), as required by the MCP specification, so that the model
%% can see and correct them.
call_tool(Name, Args) ->
    case br_mcp_tools:invoke(Name, Args) of
        {ok, Result} ->
            #{content => [text_content(br_mcp_tools:render(Name, Result))],
              structuredContent => Result,
              isError => false};
        {error, Error} ->
            #{content => [text_content(br_format:error_text(Error))],
              structuredContent => Error,
              isError => true}
    end.

text_content(Text) -> #{type => <<"text">>, text => Text}.

%%====================================================================
%% Server metadata
%%====================================================================

-spec protocol_versions() -> [binary()].
protocol_versions() -> [<<"2025-06-18">>, <<"2025-03-26">>, <<"2024-11-05">>].

-spec server_info() -> map().
server_info() ->
    #{name => <<"brazilian-soccer">>,
      title => <<"Brazilian Soccer Knowledge Graph">>,
      version => version()}.

version() ->
    case application:get_key(br_soccer, vsn) of
        {ok, Vsn} -> br_text:to_binary(Vsn);
        undefined -> <<"1.0.0">>
    end.

-spec capabilities() -> map().
capabilities() ->
    #{tools => #{listChanged => false},
      resources => #{subscribe => false, listChanged => false},
      prompts => #{listChanged => false},
      logging => #{}}.

instructions() ->
    <<"Knowledge graph over five Brazilian match data sets (Brasileirao Serie A/B/C, "
      "Copa do Brasil, Copa Libertadores; 2003-2023) and the FIFA 19 player data set. "
      "Use `ask` for a plain question, or the specific tools for structured queries. "
      "Team names are normalised, so \"Sao Paulo\", \"Sao Paulo-SP\" and "
      "\"Sao Paulo Futebol Clube\" all resolve to the same club. Standings are "
      "calculated from the match results in the data, not copied from a table, and "
      "counts are always \"in this data set\" rather than all-time.">>.

%%====================================================================
%% Resources
%%====================================================================

-spec resources() -> [map()].
resources() ->
    [#{uri => <<"soccer://datasets">>,
       name => <<"datasets">>,
       title => <<"Loaded data sets">>,
       description => <<"Files, row counts and coverage of the loaded data">>,
       mimeType => <<"application/json">>,
       read => fun() ->
                       {ok, Summary} = br_query:dataset_summary(#{}),
                       br_json:encode(Summary)
               end},
     #{uri => <<"soccer://competitions">>,
       name => <<"competitions">>,
       title => <<"Competitions">>,
       description => <<"Competitions and the seasons they cover">>,
       mimeType => <<"application/json">>,
       read => fun() ->
                       {ok, Comps} = br_query:list_competitions(#{}),
                       br_json:encode(Comps)
               end},
     #{uri => <<"soccer://teams">>,
       name => <<"teams">>,
       title => <<"Teams">>,
       description => <<"The 100 teams with the most matches in the data">>,
       mimeType => <<"application/json">>,
       read => fun() ->
                       {ok, Teams} = br_query:list_teams(#{limit => 100}),
                       br_json:encode(Teams)
               end},
     #{uri => <<"soccer://graph-schema">>,
       name => <<"graph-schema">>,
       title => <<"Knowledge graph schema">>,
       description => <<"Node types and relations of the knowledge graph">>,
       mimeType => <<"text/plain">>,
       read => fun graph_schema/0},
     #{uri => <<"soccer://sample-questions">>,
       name => <<"sample-questions">>,
       title => <<"Sample questions">>,
       description => <<"Questions this server can answer">>,
       mimeType => <<"text/plain">>,
       read => fun() -> br_text:join(br_samples:questions(), <<"\n">>) end}].

graph_schema() ->
    <<"Nodes: team:<id>, player:<fifa id>, match:<id>, competition:<id>, "
      "season:<year>, venue:<slug>, country:<name>, state:<uf>\n"
      "Edges:\n"
      "  match  -home_team->      team\n"
      "  match  -away_team->      team\n"
      "  match  -in_competition-> competition\n"
      "  match  -in_season->      season\n"
      "  match  -at_venue->       venue\n"
      "  team   -played_in->      competition\n"
      "  team   -based_in->       state\n"
      "  team   -from_country->   country\n"
      "  player -plays_for->      team\n"
      "  player -nationality->    country\n">>.

%%====================================================================
%% Prompts
%%====================================================================

-spec prompts() -> [map()].
prompts() ->
    [#{name => <<"soccer_question">>,
       title => <<"Answer a soccer question">>,
       description => <<"Answer a question about Brazilian soccer using the data">>,
       arguments => [#{name => <<"question">>,
                       description => <<"The question to answer">>,
                       required => true}],
       build => fun(Args) ->
                        Q = maps:get(<<"question">>, Args, <<"What is in the data set?">>),
                        <<"Answer this question about Brazilian soccer using the "
                          "brazilian-soccer tools. Prefer the specific tools over "
                          "`ask` when the question maps cleanly onto one, and say "
                          "which competitions and seasons the numbers come from.\n\n"
                          "Question: ", (br_text:to_binary(Q))/binary>>
                end},
     #{name => <<"scouting_report">>,
       title => <<"Club scouting report">>,
       description => <<"Summarise a club: form, record, rivals and squad">>,
       arguments => [#{name => <<"team">>,
                       description => <<"Club name, e.g. Palmeiras">>,
                       required => true},
                     #{name => <<"season">>,
                       description => <<"Season to focus on">>,
                       required => false}],
       build => fun(Args) ->
                        Team = maps:get(<<"team">>, Args, <<"Palmeiras">>),
                        Season = maps:get(<<"season">>, Args, <<"the most recent season">>),
                        <<"Write a scouting report on ", (br_text:to_binary(Team))/binary,
                          " for ", (br_text:to_binary(Season))/binary,
                          ". Use team_profile, team_stats, standings and head_to_head "
                          "against their derby rivals, and list their best rated "
                          "players with club_squad if available.">>
                end}].

%%====================================================================
%% JSON-RPC envelopes
%%====================================================================

result_response(Id, Result) ->
    #{jsonrpc => <<"2.0">>, id => Id, result => Result}.

error_response(Id, Code, Message, Data) ->
    Error = case Data of
                null -> #{code => Code, message => Message};
                _ -> #{code => Code, message => Message, data => Data}
            end,
    #{jsonrpc => <<"2.0">>, id => Id, error => Error}.
