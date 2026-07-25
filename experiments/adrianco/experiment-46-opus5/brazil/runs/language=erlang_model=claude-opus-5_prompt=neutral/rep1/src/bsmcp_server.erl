%%%-------------------------------------------------------------------
%%% @doc JSON-RPC 2.0 / Model Context Protocol request handling.
%%%
%%% Context: the protocol layer is a pure function from a decoded
%%% request term to a response term (or `noreply' for notifications),
%%% which keeps it trivially testable without a transport.  The stdio
%%% loop in {@link bsmcp_stdio} only does framing.
%%%
%%% Implemented methods: initialize, notifications/initialized, ping,
%%% tools/list, tools/call, resources/list, resources/read,
%%% prompts/list.  Tool failures (an unknown club, a missing season) are
%%% returned as a successful JSON-RPC response with `isError: true' and
%%% a helpful message, as the MCP specification requires - protocol
%%% errors are reserved for malformed requests.
%%% @end
%%%-------------------------------------------------------------------
-module(bsmcp_server).

-export([handle/1, handle_binary/1, server_info/0, protocol_versions/0]).

-define(SUPPORTED_VERSIONS, [<<"2025-06-18">>, <<"2025-03-26">>, <<"2024-11-05">>]).
-define(LATEST_VERSION, <<"2025-06-18">>).

-define(PARSE_ERROR, -32700).
-define(INVALID_REQUEST, -32600).
-define(METHOD_NOT_FOUND, -32601).
-define(INVALID_PARAMS, -32602).
-define(INTERNAL_ERROR, -32603).

%%====================================================================
%% API
%%====================================================================

server_info() ->
    #{name => <<"brazilian-soccer">>,
      title => <<"Brazilian Soccer Knowledge Graph">>,
      version => version()}.

protocol_versions() -> ?SUPPORTED_VERSIONS.

%% @doc Decode one JSON message, handle it, and encode the reply.
-spec handle_binary(binary()) -> {reply, binary()} | noreply.
handle_binary(Line) ->
    case bsmcp_json:decode(Line) of
        {error, _} ->
            {reply, bsmcp_json:encode(error_response(null, ?PARSE_ERROR,
                                                    <<"Invalid JSON">>, undefined))};
        {ok, Requests} when is_list(Requests) ->
            %% JSON-RPC batch
            Replies = [R || Req <- Requests, {reply, R} <- [handle(Req)]],
            case Replies of
                [] -> noreply;
                _ -> {reply, bsmcp_json:encode(Replies)}
            end;
        {ok, Request} ->
            case handle(Request) of
                noreply -> noreply;
                {reply, Response} -> {reply, bsmcp_json:encode(Response)}
            end
    end.

%% @doc Handle one decoded JSON-RPC message.
-spec handle(term()) -> {reply, map()} | noreply.
handle(Request) when is_map(Request) ->
    Id = maps:get(<<"id">>, Request, undefined),
    Method = maps:get(<<"method">>, Request, undefined),
    Params = case maps:get(<<"params">>, Request, #{}) of
                 P when is_map(P) -> P;
                 _ -> #{}
             end,
    case Method of
        undefined ->
            reply_error(Id, ?INVALID_REQUEST, <<"Missing method">>, undefined);
        _ ->
            try
                dispatch(Method, Params, Id)
            catch
                Class:Reason:Stack ->
                    logger:error("bsmcp: ~p ~p:~p~n~p", [Method, Class, Reason, Stack]),
                    reply_error(Id, ?INTERNAL_ERROR, <<"Internal error">>,
                                #{method => Method,
                                  reason => iolist_to_binary(io_lib:format("~p", [Reason]))})
            end
    end;
handle(_) ->
    {reply, error_response(null, ?INVALID_REQUEST, <<"Invalid request">>, undefined)}.

%%====================================================================
%% Methods
%%====================================================================

dispatch(<<"initialize">>, Params, Id) ->
    Requested = maps:get(<<"protocolVersion">>, Params, ?LATEST_VERSION),
    Version = case lists:member(Requested, ?SUPPORTED_VERSIONS) of
                  true -> Requested;
                  false -> ?LATEST_VERSION
              end,
    reply(Id, #{protocolVersion => Version,
                capabilities => #{tools => #{listChanged => false},
                                  resources => #{listChanged => false,
                                                 subscribe => false}},
                serverInfo => server_info(),
                instructions => instructions()});
dispatch(<<"notifications/initialized">>, _Params, _Id) ->
    noreply;
dispatch(<<"notifications/cancelled">>, _Params, _Id) ->
    noreply;
dispatch(<<"ping">>, _Params, Id) ->
    reply(Id, #{});
dispatch(<<"tools/list">>, _Params, Id) ->
    reply(Id, #{tools => bsmcp_tools:list()});
dispatch(<<"tools/call">>, Params, Id) ->
    case maps:get(<<"name">>, Params, undefined) of
        undefined ->
            reply_error(Id, ?INVALID_PARAMS, <<"Missing tool name">>, undefined);
        Name ->
            Args = case maps:get(<<"arguments">>, Params, #{}) of
                       A when is_map(A) -> A;
                       _ -> #{}
                   end,
            bsmcp_data:ensure_loaded(),
            case bsmcp_tools:call(Name, Args) of
                {ok, Structured, Text} ->
                    reply(Id, tool_result(Text, Structured, false));
                {error, Structured, Text} ->
                    reply(Id, tool_result(Text, Structured, true))
            end
    end;
dispatch(<<"resources/list">>, _Params, Id) ->
    reply(Id, #{resources => resources()});
dispatch(<<"resources/read">>, Params, Id) ->
    case maps:get(<<"uri">>, Params, undefined) of
        undefined ->
            reply_error(Id, ?INVALID_PARAMS, <<"Missing uri">>, undefined);
        Uri ->
            case read_resource(Uri) of
                {ok, MimeType, Text} ->
                    reply(Id, #{contents => [#{uri => Uri,
                                               mimeType => MimeType,
                                               text => Text}]});
                error ->
                    reply_error(Id, ?INVALID_PARAMS, <<"Unknown resource">>, #{uri => Uri})
            end
    end;
dispatch(<<"prompts/list">>, _Params, Id) ->
    reply(Id, #{prompts => []});
dispatch(<<"resources/templates/list">>, _Params, Id) ->
    reply(Id, #{resourceTemplates => []});
dispatch(Method, _Params, Id) ->
    reply_error(Id, ?METHOD_NOT_FOUND, <<"Method not found">>, #{method => Method}).

instructions() ->
    <<"Knowledge graph over six Brazilian football datasets: 17k de-duplicated "
      "matches (Brasileirão Série A/B/C, Copa do Brasil, Copa Libertadores, "
      "2003-2023) and 18k FIFA player records. Club names are normalised, so "
      "'Atletico-MG', 'Atlético Mineiro' and 'Clube Atlético Mineiro' all "
      "resolve to the same club; ambiguous names such as Botafogo are kept "
      "apart by state. League tables, records and averages are calculated from "
      "the match results. The datasets contain no goal scorer, lineup or "
      "transfer information."/utf8>>.

tool_result(Text, Structured, IsError) ->
    #{content => [#{type => <<"text">>, text => Text}],
      structuredContent => Structured,
      isError => IsError}.

%%====================================================================
%% Resources
%%====================================================================

resources() ->
    [#{uri => <<"bsmcp://dataset/summary">>,
       name => <<"dataset-summary">>,
       title => <<"Dataset summary">>,
       description => <<"Files, row counts, competitions and seasons loaded">>,
       mimeType => <<"text/plain">>},
     #{uri => <<"bsmcp://dataset/sources">>,
       name => <<"dataset-sources">>,
       title => <<"Source files and licences">>,
       description => <<"Provenance and licence of each CSV file">>,
       mimeType => <<"text/markdown">>},
     #{uri => <<"bsmcp://teams">>,
       name => <<"teams">>,
       title => <<"Canonical teams">>,
       description => <<"Every club with its normalised name and the spellings "
                        "found in the source files">>,
       mimeType => <<"application/json">>},
     #{uri => <<"bsmcp://competitions">>,
       name => <<"competitions">>,
       title => <<"Competitions and seasons">>,
       description => <<"Competition keys, display names and available seasons">>,
       mimeType => <<"application/json">>}].

read_resource(<<"bsmcp://dataset/summary">>) ->
    bsmcp_data:ensure_loaded(),
    {ok, <<"text/plain">>,
     bsmcp_format:render(dataset_summary, bsmcp_query:dataset_summary())};
read_resource(<<"bsmcp://dataset/sources">>) ->
    {ok, <<"text/markdown">>, sources_markdown()};
read_resource(<<"bsmcp://teams">>) ->
    bsmcp_data:ensure_loaded(),
    Teams = bsmcp_query:list_teams(#{limit => 1000}),
    {ok, <<"application/json">>, bsmcp_json:encode(Teams)};
read_resource(<<"bsmcp://competitions">>) ->
    bsmcp_data:ensure_loaded(),
    Comps = [#{key => K,
               name => bsmcp_data:competition_name(K),
               seasons => bsmcp_data:seasons(K)} || K <- bsmcp_data:competitions()],
    {ok, <<"application/json">>, bsmcp_json:encode(#{competitions => Comps})};
read_resource(_) ->
    error.

sources_markdown() ->
    <<"# Source datasets\n\n"
      "| File | Competition | Licence |\n"
      "|---|---|---|\n"
      "| Brasileirao_Matches.csv | Brasileirão Série A 2012-2022 | CC BY 4.0 |\n"
      "| Brazilian_Cup_Matches.csv | Copa do Brasil 2012-2021 | CC BY 4.0 |\n"
      "| Libertadores_Matches.csv | Copa Libertadores 2013-2022 | CC BY 4.0 |\n"
      "| BR-Football-Dataset.csv | Série A/B/C and Copa do Brasil 2014-2023, "
      "with shots, attacks and corners | CC0 |\n"
      "| novo_campeonato_brasileiro.csv | Brasileirão Série A 2003-2019, with "
      "stadiums | CC BY 4.0 |\n"
      "| fifa_data.csv | 18,207 FIFA player records | Apache 2.0 |\n\n"
      "The three Série A sources overlap. Fixtures are de-duplicated on "
      "(competition, season, home, away) and merged, so each fixture is counted "
      "once while keeping the round, stadium and match statistics contributed by "
      "each file.\n\n"
      "Not present in any source: goal scorers, line-ups, cards, transfers.\n"/utf8>>.

%%====================================================================
%% Helpers
%%====================================================================

reply(undefined, _Result) -> noreply;
reply(Id, Result) -> {reply, #{jsonrpc => <<"2.0">>, id => Id, result => Result}}.

reply_error(undefined, _Code, _Message, _Data) -> noreply;
reply_error(Id, Code, Message, Data) -> {reply, error_response(Id, Code, Message, Data)}.

error_response(Id, Code, Message, Data) ->
    Error = case Data of
                undefined -> #{code => Code, message => Message};
                _ -> #{code => Code, message => Message, data => Data}
            end,
    #{jsonrpc => <<"2.0">>, id => Id, error => Error}.

version() ->
    case application:get_key(bsmcp, vsn) of
        {ok, Vsn} -> bsmcp_text:bin(Vsn);
        undefined -> <<"1.0.0">>
    end.
