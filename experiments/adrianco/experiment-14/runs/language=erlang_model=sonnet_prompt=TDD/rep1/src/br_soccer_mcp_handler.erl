-module(br_soccer_mcp_handler).
-export([handle/2, encode_json/1, decode_json/1]).

-define(PROTOCOL_VERSION, <<"2024-11-05">>).
-define(SERVER_NAME, <<"br-soccer-mcp">>).
-define(SERVER_VERSION, <<"0.1.0">>).

encode_json(Map) ->
    jsx:encode(Map).

decode_json(Bin) ->
    jsx:decode(Bin, [return_maps]).

handle(Req, Data) ->
    Id     = maps:get(<<"id">>, Req, null),
    Method = maps:get(<<"method">>, Req, <<>>),
    Params = maps:get(<<"params">>, Req, #{}),
    case dispatch(Method, Params, Data) of
        {ok, Result} ->
            {ok, jsonrpc_result(Id, Result)};
        {error, Code, Msg} ->
            {ok, jsonrpc_error(Id, Code, Msg)}
    end.

jsonrpc_result(Id, Result) ->
    #{<<"jsonrpc">> => <<"2.0">>,
      <<"id">>      => Id,
      <<"result">>  => Result}.

jsonrpc_error(Id, Code, Msg) ->
    #{<<"jsonrpc">> => <<"2.0">>,
      <<"id">>      => Id,
      <<"error">>   => #{<<"code">> => Code, <<"message">> => Msg}}.

dispatch(<<"initialize">>, _Params, _Data) ->
    {ok, #{
        <<"protocolVersion">> => ?PROTOCOL_VERSION,
        <<"serverInfo">> => #{
            <<"name">>    => ?SERVER_NAME,
            <<"version">> => ?SERVER_VERSION
        },
        <<"capabilities">> => #{
            <<"tools">> => #{<<"listChanged">> => false}
        }
    }};

dispatch(<<"initialized">>, _Params, _Data) ->
    {ok, #{}};

dispatch(<<"tools/list">>, _Params, _Data) ->
    {ok, #{<<"tools">> => tool_definitions()}};

dispatch(<<"tools/call">>, Params, Data) ->
    ToolName = maps:get(<<"name">>, Params, <<>>),
    Args     = maps:get(<<"arguments">>, Params, #{}),
    call_tool(ToolName, Args, Data);

dispatch(_, _, _) ->
    {error, -32601, <<"Method not found">>}.

%% ── Tool definitions ──────────────────────────────────────────────────────────

tool_definitions() ->
    [
        #{<<"name">> => <<"search_matches">>,
          <<"description">> => <<"Search for matches by team, season, or competition">>,
          <<"inputSchema">> => #{
              <<"type">> => <<"object">>,
              <<"properties">> => #{
                  <<"team">>        => #{<<"type">> => <<"string">>, <<"description">> => <<"Team name (partial match)">>},
                  <<"season">>      => #{<<"type">> => <<"string">>, <<"description">> => <<"Season year e.g. 2023">>},
                  <<"competition">> => #{<<"type">> => <<"string">>,
                                        <<"description">> => <<"brasileirao|copa_brasil|libertadores|br_football|historical">>},
                  <<"limit">>       => #{<<"type">> => <<"integer">>, <<"description">> => <<"Max results (default 20)">>}
              }
          }},
        #{<<"name">> => <<"team_stats">>,
          <<"description">> => <<"Get win/draw/loss record and goal statistics for a team">>,
          <<"inputSchema">> => #{
              <<"type">> => <<"object">>,
              <<"properties">> => #{
                  <<"team">>        => #{<<"type">> => <<"string">>, <<"description">> => <<"Team name">>},
                  <<"season">>      => #{<<"type">> => <<"string">>, <<"description">> => <<"Season year (optional)">>},
                  <<"competition">> => #{<<"type">> => <<"string">>, <<"description">> => <<"Competition filter (optional)">>}
              },
              <<"required">> => [<<"team">>]
          }},
        #{<<"name">> => <<"head_to_head">>,
          <<"description">> => <<"Compare two teams head-to-head">>,
          <<"inputSchema">> => #{
              <<"type">> => <<"object">>,
              <<"properties">> => #{
                  <<"team1">>  => #{<<"type">> => <<"string">>},
                  <<"team2">>  => #{<<"type">> => <<"string">>},
                  <<"season">> => #{<<"type">> => <<"string">>}
              },
              <<"required">> => [<<"team1">>, <<"team2">>]
          }},
        #{<<"name">> => <<"search_players">>,
          <<"description">> => <<"Search FIFA player database">>,
          <<"inputSchema">> => #{
              <<"type">> => <<"object">>,
              <<"properties">> => #{
                  <<"name">>        => #{<<"type">> => <<"string">>, <<"description">> => <<"Player name (partial)">>},
                  <<"nationality">> => #{<<"type">> => <<"string">>, <<"description">> => <<"e.g. Brazil">>},
                  <<"club">>        => #{<<"type">> => <<"string">>, <<"description">> => <<"Club name (partial)">>},
                  <<"position">>    => #{<<"type">> => <<"string">>, <<"description">> => <<"e.g. ST, GK, CM">>},
                  <<"min_overall">> => #{<<"type">> => <<"integer">>, <<"description">> => <<"Minimum FIFA rating">>},
                  <<"limit">>       => #{<<"type">> => <<"integer">>}
              }
          }},
        #{<<"name">> => <<"competition_standings">>,
          <<"description">> => <<"Calculate standings table for a competition and season">>,
          <<"inputSchema">> => #{
              <<"type">> => <<"object">>,
              <<"properties">> => #{
                  <<"competition">> => #{<<"type">> => <<"string">>,
                                        <<"description">> => <<"brasileirao|copa_brasil|libertadores|historical">>},
                  <<"season">>      => #{<<"type">> => <<"string">>, <<"description">> => <<"Year e.g. 2019">>}
              },
              <<"required">> => [<<"competition">>, <<"season">>]
          }},
        #{<<"name">> => <<"biggest_matches">>,
          <<"description">> => <<"Find matches with the biggest goal differences">>,
          <<"inputSchema">> => #{
              <<"type">> => <<"object">>,
              <<"properties">> => #{
                  <<"competition">> => #{<<"type">> => <<"string">>},
                  <<"season">>      => #{<<"type">> => <<"string">>},
                  <<"limit">>       => #{<<"type">> => <<"integer">>, <<"description">> => <<"Default 10">>}
              }
          }}
    ].

%% ── Tool implementations ──────────────────────────────────────────────────────

call_tool(<<"search_matches">>, Args, Data) ->
    AllMatches = br_soccer_data:all_matches(Data),
    Filtered1 = case maps:get(<<"competition">>, Args, undefined) of
        undefined -> AllMatches;
        Comp -> [M || M <- AllMatches, match_competition(M, Comp)]
    end,
    Filtered2 = case maps:get(<<"season">>, Args, undefined) of
        undefined -> Filtered1;
        S -> br_soccer_query:filter_by_season(Filtered1, S)
    end,
    Filtered3 = case maps:get(<<"team">>, Args, undefined) of
        undefined -> Filtered2;
        T -> br_soccer_query:filter_by_team(Filtered2, T)
    end,
    Limit = to_int(maps:get(<<"limit">>, Args, 20)),
    Results = lists:sublist(Filtered3, Limit),
    Total = length(Filtered3),
    Text = format_matches(Results, Total),
    {ok, text_content(Text)};

call_tool(<<"team_stats">>, Args, Data) ->
    Team = maps:get(<<"team">>, Args, <<>>),
    AllMatches = br_soccer_data:all_matches(Data),
    Filtered1 = case maps:get(<<"competition">>, Args, undefined) of
        undefined -> AllMatches;
        Comp -> [M || M <- AllMatches, match_competition(M, Comp)]
    end,
    Filtered2 = case maps:get(<<"season">>, Args, undefined) of
        undefined -> Filtered1;
        S -> br_soccer_query:filter_by_season(Filtered1, S)
    end,
    Stats = br_soccer_query:team_stats(Filtered2, Team),
    Text = format_team_stats(Team, Stats, Args),
    {ok, text_content(Text)};

call_tool(<<"head_to_head">>, Args, Data) ->
    T1 = maps:get(<<"team1">>, Args, <<>>),
    T2 = maps:get(<<"team2">>, Args, <<>>),
    AllMatches = br_soccer_data:all_matches(Data),
    Matches = case maps:get(<<"season">>, Args, undefined) of
        undefined -> AllMatches;
        S -> br_soccer_query:filter_by_season(AllMatches, S)
    end,
    H2H = br_soccer_query:head_to_head(Matches, T1, T2),
    Text = format_h2h(T1, T2, H2H),
    {ok, text_content(Text)};

call_tool(<<"search_players">>, Args, Data) ->
    Players = maps:get(players, Data, []),
    Filters = build_player_filters(Args),
    Results = br_soccer_query:search_players(Players, Filters),
    Limit = to_int(maps:get(<<"limit">>, Args, 20)),
    Top = lists:sublist(
            lists:sort(fun(A, B) ->
                to_int(maps:get(<<"Overall">>, A, <<"0">>)) >
                to_int(maps:get(<<"Overall">>, B, <<"0">>))
            end, Results),
            Limit),
    Text = format_players(Top, length(Results)),
    {ok, text_content(Text)};

call_tool(<<"competition_standings">>, Args, Data) ->
    CompStr = maps:get(<<"competition">>, Args, <<"brasileirao">>),
    Season  = maps:get(<<"season">>, Args, undefined),
    Comp    = binary_to_competition(CompStr),
    CompMatches = maps:get(Comp, Data, []),
    Filtered = case Season of
        undefined -> CompMatches;
        S -> br_soccer_query:filter_by_season(CompMatches, S)
    end,
    Standings = br_soccer_query:compute_standings(Filtered),
    Text = format_standings(CompStr, Season, Standings),
    {ok, text_content(Text)};

call_tool(<<"biggest_matches">>, Args, Data) ->
    AllMatches = br_soccer_data:all_matches(Data),
    Filtered1 = case maps:get(<<"competition">>, Args, undefined) of
        undefined -> AllMatches;
        Comp -> [M || M <- AllMatches, match_competition(M, Comp)]
    end,
    Filtered2 = case maps:get(<<"season">>, Args, undefined) of
        undefined -> Filtered1;
        S -> br_soccer_query:filter_by_season(Filtered1, S)
    end,
    Limit = to_int(maps:get(<<"limit">>, Args, 10)),
    Results = br_soccer_query:biggest_matches(Filtered2, Limit),
    Text = format_biggest(Results),
    {ok, text_content(Text)};

call_tool(Name, _Args, _Data) ->
    {error, -32602, <<"Unknown tool: ", Name/binary>>}.

%% ── Helpers ───────────────────────────────────────────────────────────────────

text_content(Text) ->
    #{<<"content">> => [#{<<"type">> => <<"text">>, <<"text">> => Text}]}.

match_competition(M, CompStr) ->
    Comp = binary_to_competition(CompStr),
    maps:get(competition, M, undefined) =:= Comp.

binary_to_competition(<<"brasileirao">>)  -> brasileirao;
binary_to_competition(<<"copa_brasil">>)  -> copa_brasil;
binary_to_competition(<<"libertadores">>) -> libertadores;
binary_to_competition(<<"br_football">>)  -> br_football;
binary_to_competition(<<"historical">>)   -> historical;
binary_to_competition(_)                  -> unknown.

build_player_filters(Args) ->
    Keys = [{<<"name">>, name}, {<<"nationality">>, nationality},
            {<<"club">>, club}, {<<"position">>, position},
            {<<"min_overall">>, min_overall}],
    lists:foldl(fun({ArgKey, FilterKey}, Acc) ->
        case maps:get(ArgKey, Args, undefined) of
            undefined -> Acc;
            Val -> Acc#{FilterKey => Val}
        end
    end, #{}, Keys).

to_int(B) when is_binary(B) ->
    try binary_to_integer(string:trim(B)) catch _:_ -> 0 end;
to_int(N) when is_integer(N) -> N;
to_int(_) -> 0.

get_team_field(M) ->
    Home = find_field(M, [<<"home_team">>, <<"home">>, <<"Equipe_mandante">>]),
    Away = find_field(M, [<<"away_team">>, <<"away">>, <<"Equipe_visitante">>]),
    {br_soccer_csv:normalize_team(Home), br_soccer_csv:normalize_team(Away)}.

find_field(_M, []) -> <<>>;
find_field(M, [K | Rest]) ->
    case maps:get(K, M, undefined) of
        undefined -> find_field(M, Rest);
        V -> V
    end.

%% ── Formatters ────────────────────────────────────────────────────────────────

format_matches(Matches, Total) ->
    Lines = [format_match_line(M) || M <- Matches],
    Shown = length(Matches),
    Header = if Total > Shown ->
                   iolist_to_binary(io_lib:format("Found ~w matches (showing ~w):\n", [Total, Shown]));
               true ->
                   iolist_to_binary(io_lib:format("Found ~w matches:\n", [Total]))
             end,
    iolist_to_binary([Header | Lines]).

format_match_line(M) ->
    {Home, Away} = get_team_field(M),
    HG = to_int(maps:get(<<"home_goal">>, M, <<"0">>)),
    AG = to_int(maps:get(<<"away_goal">>, M, <<"0">>)),
    Date = maps:get(<<"datetime">>, M, maps:get(<<"date">>, M, <<>>)),
    Comp = atom_to_binary(maps:get(competition, M, unknown), utf8),
    Season = maps:get(<<"season">>, M, <<>>),
    iolist_to_binary(io_lib:format("  ~s: ~s ~w-~w ~s (~s ~s)\n",
        [Date, Home, HG, AG, Away, Comp, Season])).

format_team_stats(Team, Stats, Args) ->
    M = maps:get(matches, Stats, 0),
    W = maps:get(wins, Stats, 0),
    D = maps:get(draws, Stats, 0),
    L = maps:get(losses, Stats, 0),
    GF = maps:get(goals_for, Stats, 0),
    GA = maps:get(goals_against, Stats, 0),
    Pts = W*3 + D,
    WinRate = if M > 0 -> round(W * 1000 / M) / 10; true -> 0.0 end,
    SeasonStr = case maps:get(<<"season">>, Args, undefined) of
        undefined -> <<"all seasons">>;
        S -> S
    end,
    CompStr = case maps:get(<<"competition">>, Args, undefined) of
        undefined -> <<"all competitions">>;
        C -> C
    end,
    iolist_to_binary(io_lib:format(
        "~s statistics (~s, ~s):\n"
        "  matches: ~w\n"
        "  Record: ~wW ~wD ~wL\n"
        "  Points: ~w\n"
        "  Goals For: ~w, Goals Against: ~w, GD: ~w\n"
        "  Win rate: ~.1f%\n",
        [Team, SeasonStr, CompStr, M, W, D, L, Pts, GF, GA, GF-GA, WinRate])).

format_h2h(T1, T2, Matches) ->
    Total = length(Matches),
    {T1W, T2W, Draws} = lists:foldl(fun(M, {A1, A2, Draws}) ->
        Home = br_soccer_csv:normalize_team(
                 maps:get(<<"home_team">>, M, maps:get(<<"home">>, M, <<>>))),
        HG = to_int(maps:get(<<"home_goal">>, M, <<"0">>)),
        AG = to_int(maps:get(<<"away_goal">>, M, <<"0">>)),
        T1IsHome = br_soccer_query:team_name_matches(Home, T1),
        if HG =:= AG -> {A1, A2, Draws+1};
           T1IsHome andalso HG > AG -> {A1+1, A2, Draws};
           T1IsHome andalso HG < AG -> {A1, A2+1, Draws};
           not T1IsHome andalso AG > HG -> {A1+1, A2, Draws};
           true -> {A1, A2+1, Draws}
        end
    end, {0, 0, 0}, Matches),
    Header = iolist_to_binary(io_lib:format(
        "Head-to-head: ~s vs ~s (~w matches)\n"
        "  ~s wins: ~w\n"
        "  ~s wins: ~w\n"
        "  Draws: ~w\n\n",
        [T1, T2, Total, T1, T1W, T2, T2W, Draws])),
    Lines = [format_match_line(M) || M <- lists:sublist(Matches, 10)],
    iolist_to_binary([Header | Lines]).

format_standings(Comp, Season, Standings) ->
    SeasonStr = case Season of undefined -> <<"all seasons">>; S -> S end,
    Header = iolist_to_binary(io_lib:format(
        "~s standings (~s):\n", [Comp, SeasonStr])),
    Rows = lists:zipwith(fun(Pos, {Team, S}) ->
        P = maps:get(points, S, 0),
        W = maps:get(wins, S, 0),
        D = maps:get(draws, S, 0),
        L = maps:get(losses, S, 0),
        GF = maps:get(gf, S, 0),
        GA = maps:get(ga, S, 0),
        iolist_to_binary(io_lib:format(
            "  ~2w. ~s - ~w pts (~wW ~wD ~wL) GD:~w\n",
            [Pos, Team, P, W, D, L, GF-GA]))
    end, lists:seq(1, length(Standings)), Standings),
    iolist_to_binary([Header | Rows]).

format_players(Players, Total) ->
    Header = iolist_to_binary(io_lib:format(
        "Found ~w players (showing ~w):\n", [Total, length(Players)])),
    Rows = lists:map(fun(P) ->
        Name = maps:get(<<"Name">>, P, <<>>),
        Club = maps:get(<<"Club">>, P, <<>>),
        Nat  = maps:get(<<"Nationality">>, P, <<>>),
        Ovr  = maps:get(<<"Overall">>, P, <<>>),
        Pos  = maps:get(<<"Position">>, P, <<>>),
        Age  = maps:get(<<"Age">>, P, <<>>),
        iolist_to_binary(io_lib:format(
            "  ~s (Age ~s, ~s) - ~s | ~s | Rating: ~s\n",
            [Name, Age, Nat, Club, Pos, Ovr]))
    end, Players),
    iolist_to_binary([Header | Rows]).

format_biggest(Results) ->
    Header = iolist_to_binary(io_lib:format(
        "Top ~w matches by goal difference:\n", [length(Results)])),
    Rows = lists:zipwith(fun(Pos, {Date, Home, Away, HG, AG}) ->
        Diff = abs(HG - AG),
        iolist_to_binary(io_lib:format(
            "  ~w. ~s: ~s ~w-~w ~s (diff: ~w)\n",
            [Pos, Date, Home, HG, AG, Away, Diff]))
    end, lists:seq(1, length(Results)), Results),
    iolist_to_binary([Header | Rows]).
