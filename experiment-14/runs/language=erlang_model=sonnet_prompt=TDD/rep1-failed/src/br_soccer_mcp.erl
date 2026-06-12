-module(br_soccer_mcp).
-export([handle_request/2, encode_json/1, decode_json/1,
         format_matches/1, format_players/1, format_standings/1,
         start/0]).

-define(PROTOCOL_VERSION, <<"2024-11-05">>).
-define(SERVER_NAME, <<"br-soccer-mcp">>).
-define(SERVER_VERSION, <<"0.1.0">>).
-define(DATA_DIR, "data/kaggle/").

%%% JSON encoding using OTP 27+ built-in json module

encode_json(Value) ->
    binary_to_list(iolist_to_binary(json:encode(value_to_json(Value)))).

decode_json(Json) when is_list(Json) ->
    decode_json(list_to_binary(Json));
decode_json(Json) when is_binary(Json) ->
    json:decode(Json).

value_to_json(Map) when is_map(Map) ->
    maps:map(fun(_K, V) -> value_to_json(V) end, Map);
value_to_json(List) when is_list(List) ->
    [value_to_json(V) || V <- List];
value_to_json(V) -> V.

%%% MCP request handling

handle_request(Req, State) ->
    Method = maps:get(<<"method">>, Req, <<>>),
    Id = maps:get(<<"id">>, Req, undefined),
    Params = maps:get(<<"params">>, Req, #{}),
    case Id of
        undefined ->
            %% Notification, no response needed
            notification;
        _ ->
            case handle_method(Method, Params, State) of
                {ok, Result} ->
                    #{<<"jsonrpc">> => <<"2.0">>, <<"id">> => Id,
                      <<"result">> => Result};
                {error, Code, Msg} ->
                    #{<<"jsonrpc">> => <<"2.0">>, <<"id">> => Id,
                      <<"error">> => #{<<"code">> => Code, <<"message">> => Msg}}
            end
    end.

handle_method(<<"initialize">>, _Params, _State) ->
    {ok, #{
        <<"protocolVersion">> => ?PROTOCOL_VERSION,
        <<"capabilities">> => #{<<"tools">> => #{}},
        <<"serverInfo">> => #{<<"name">> => ?SERVER_NAME, <<"version">> => ?SERVER_VERSION}
    }};

handle_method(<<"tools/list">>, _Params, _State) ->
    {ok, #{<<"tools">> => tool_definitions()}};

handle_method(<<"tools/call">>, Params, State) ->
    ToolName = maps:get(<<"name">>, Params, <<>>),
    Args = maps:get(<<"arguments">>, Params, #{}),
    handle_tool_call(ToolName, Args, State);

handle_method(_, _, _) ->
    {error, -32601, <<"Method not found">>}.

%%% Tool definitions

tool_definitions() ->
    [
        #{<<"name">> => <<"find_matches">>,
          <<"description">> => <<"Find matches by team, season, competition, or date range">>,
          <<"inputSchema">> => #{
              <<"type">> => <<"object">>,
              <<"properties">> => #{
                  <<"team">> => #{<<"type">> => <<"string">>, <<"description">> => <<"Team name (partial match)">>},
                  <<"season">> => #{<<"type">> => <<"integer">>, <<"description">> => <<"Season year">>},
                  <<"competition">> => #{<<"type">> => <<"string">>, <<"description">> => <<"brasileirao, copa_do_brasil, or libertadores">>},
                  <<"home_or_away">> => #{<<"type">> => <<"string">>, <<"description">> => <<"home, away, or all (default: all)">>},
                  <<"limit">> => #{<<"type">> => <<"integer">>, <<"description">> => <<"Max results (default: 20)">>}
              }
          }},
        #{<<"name">> => <<"team_stats">>,
          <<"description">> => <<"Get win/loss/draw statistics for a team">>,
          <<"inputSchema">> => #{
              <<"type">> => <<"object">>,
              <<"required">> => [<<"team">>],
              <<"properties">> => #{
                  <<"team">> => #{<<"type">> => <<"string">>},
                  <<"season">> => #{<<"type">> => <<"integer">>},
                  <<"competition">> => #{<<"type">> => <<"string">>}
              }
          }},
        #{<<"name">> => <<"find_players">>,
          <<"description">> => <<"Search for players by name, nationality, club, or position">>,
          <<"inputSchema">> => #{
              <<"type">> => <<"object">>,
              <<"properties">> => #{
                  <<"name">> => #{<<"type">> => <<"string">>},
                  <<"nationality">> => #{<<"type">> => <<"string">>},
                  <<"club">> => #{<<"type">> => <<"string">>},
                  <<"position">> => #{<<"type">> => <<"string">>},
                  <<"min_overall">> => #{<<"type">> => <<"integer">>},
                  <<"limit">> => #{<<"type">> => <<"integer">>}
              }
          }},
        #{<<"name">> => <<"season_standings">>,
          <<"description">> => <<"Calculate league standings for a given season">>,
          <<"inputSchema">> => #{
              <<"type">> => <<"object">>,
              <<"required">> => [<<"season">>],
              <<"properties">> => #{
                  <<"season">> => #{<<"type">> => <<"integer">>},
                  <<"competition">> => #{<<"type">> => <<"string">>}
              }
          }},
        #{<<"name">> => <<"head_to_head">>,
          <<"description">> => <<"Get head-to-head record between two teams">>,
          <<"inputSchema">> => #{
              <<"type">> => <<"object">>,
              <<"required">> => [<<"team1">>, <<"team2">>],
              <<"properties">> => #{
                  <<"team1">> => #{<<"type">> => <<"string">>},
                  <<"team2">> => #{<<"type">> => <<"string">>}
              }
          }},
        #{<<"name">> => <<"biggest_wins">>,
          <<"description">> => <<"Find the biggest victory margins in the dataset">>,
          <<"inputSchema">> => #{
              <<"type">> => <<"object">>,
              <<"properties">> => #{
                  <<"limit">> => #{<<"type">> => <<"integer">>}
              }
          }},
        #{<<"name">> => <<"avg_goals">>,
          <<"description">> => <<"Calculate average goals per match for a competition">>,
          <<"inputSchema">> => #{
              <<"type">> => <<"object">>,
              <<"properties">> => #{
                  <<"competition">> => #{<<"type">> => <<"string">>}
              }
          }},
        #{<<"name">> => <<"best_home_records">>,
          <<"description">> => <<"Find teams with the best home win rates">>,
          <<"inputSchema">> => #{
              <<"type">> => <<"object">>,
              <<"properties">> => #{
                  <<"competition">> => #{<<"type">> => <<"string">>},
                  <<"limit">> => #{<<"type">> => <<"integer">>}
              }
          }}
    ].

%%% Tool call dispatch
handle_tool_call(<<"find_matches">>, Args, State) ->
    Team = binary_to_list(maps:get(<<"team">>, Args, <<>>)),
    Season = maps:get(<<"season">>, Args, 0),
    Competition = binary_to_list(maps:get(<<"competition">>, Args, <<>>)),
    HomeAway = case maps:get(<<"home_or_away">>, Args, <<"all">>) of
        <<"home">> -> home; <<"away">> -> away; _ -> all
    end,
    Limit = maps:get(<<"limit">>, Args, 20),
    Matches0 = case Team of
        "" -> br_soccer_query:find_matches_by_competition(State, Competition);
        T  -> br_soccer_query:find_matches_by_team(State, T, HomeAway)
    end,
    Matches1 = if
        Season > 0 -> [M || M <- Matches0, maps:get(season, M, 0) =:= Season];
        true -> Matches0
    end,
    Matches2 = if
        Competition =/= "" ->
            CompLow = string:lowercase(Competition),
            [M || M <- Matches1,
                  string:find(string:lowercase(maps:get(competition, M, "")), CompLow) =/= nomatch orelse
                  string:find(string:lowercase(maps:get(tournament, M, "")), CompLow) =/= nomatch];
        true -> Matches1
    end,
    Result = lists:sublist(Matches2, Limit),
    {ok, #{<<"content">> => [#{<<"type">> => <<"text">>,
                                <<"text">> => list_to_binary(format_matches(Result))}]}};

handle_tool_call(<<"team_stats">>, Args, State) ->
    Team = binary_to_list(maps:get(<<"team">>, Args, <<>>)),
    Season = maps:get(<<"season">>, Args, 0),
    Competition = binary_to_list(maps:get(<<"competition">>, Args, <<"brasileirao">>)),
    Stats = br_soccer_query:team_stats(State, Team, Competition, Season),
    {ok, #{<<"content">> => [#{<<"type">> => <<"text">>,
                                <<"text">> => list_to_binary(format_team_stats(Team, Season, Competition, Stats))}]}};

handle_tool_call(<<"find_players">>, Args, State) ->
    Name = binary_to_list(maps:get(<<"name">>, Args, <<>>)),
    Nationality = binary_to_list(maps:get(<<"nationality">>, Args, <<>>)),
    Club = binary_to_list(maps:get(<<"club">>, Args, <<>>)),
    Position = binary_to_list(maps:get(<<"position">>, Args, <<>>)),
    MinOverall = maps:get(<<"min_overall">>, Args, 0),
    Limit = maps:get(<<"limit">>, Args, 20),
    Players = case Name of
        "" -> br_soccer_query:top_players(State, #{
                nationality => Nationality, club => Club,
                position => Position, limit => Limit});
        N  -> Filtered = br_soccer_query:find_players_by_name(State, N),
              lists:sublist(Filtered, Limit)
    end,
    WithMin = [P || P <- Players, maps:get(overall, P, 0) >= MinOverall],
    {ok, #{<<"content">> => [#{<<"type">> => <<"text">>,
                                <<"text">> => list_to_binary(format_players(WithMin))}]}};

handle_tool_call(<<"season_standings">>, Args, State) ->
    Season = maps:get(<<"season">>, Args, 0),
    Competition = binary_to_list(maps:get(<<"competition">>, Args, <<"brasileirao">>)),
    Standings = br_soccer_query:season_standings(State, Season, Competition),
    {ok, #{<<"content">> => [#{<<"type">> => <<"text">>,
                                <<"text">> => list_to_binary(format_standings(Standings))}]}};

handle_tool_call(<<"head_to_head">>, Args, State) ->
    T1 = binary_to_list(maps:get(<<"team1">>, Args, <<>>)),
    T2 = binary_to_list(maps:get(<<"team2">>, Args, <<>>)),
    Result = br_soccer_query:head_to_head(State, T1, T2),
    {ok, #{<<"content">> => [#{<<"type">> => <<"text">>,
                                <<"text">> => list_to_binary(format_h2h(T1, T2, Result))}]}};

handle_tool_call(<<"biggest_wins">>, Args, State) ->
    Limit = maps:get(<<"limit">>, Args, 10),
    Wins = br_soccer_query:biggest_wins(State, Limit),
    Lines = lists:map(fun({M, Diff}) ->
        io_lib:format("~s ~w-~w ~s (diff: ~w)~n",
            [maps:get(home_team, M, "?"), maps:get(home_goal, M, 0),
             maps:get(away_goal, M, 0), maps:get(away_team, M, "?"), Diff])
    end, Wins),
    {ok, #{<<"content">> => [#{<<"type">> => <<"text">>,
                                <<"text">> => list_to_binary(lists:flatten(Lines))}]}};

handle_tool_call(<<"avg_goals">>, Args, State) ->
    Competition = binary_to_list(maps:get(<<"competition">>, Args, <<"brasileirao">>)),
    Avg = br_soccer_query:avg_goals_per_match(State, Competition),
    Text = io_lib:format("Average goals per match (~s): ~.2f~n", [Competition, Avg]),
    {ok, #{<<"content">> => [#{<<"type">> => <<"text">>,
                                <<"text">> => list_to_binary(lists:flatten(Text))}]}};

handle_tool_call(<<"best_home_records">>, Args, State) ->
    Competition = binary_to_list(maps:get(<<"competition">>, Args, <<"brasileirao">>)),
    Limit = maps:get(<<"limit">>, Args, 10),
    Records = br_soccer_query:best_home_records(State, Competition, Limit),
    Lines = lists:zipwith(fun(N, {Team, WinRate}) ->
        io_lib:format("~w. ~s - ~.1f% home win rate~n", [N, Team, WinRate * 100])
    end, lists:seq(1, length(Records)), Records),
    {ok, #{<<"content">> => [#{<<"type">> => <<"text">>,
                                <<"text">> => list_to_binary(lists:flatten(Lines))}]}};

handle_tool_call(ToolName, _Args, _State) ->
    {error, -32602, iolist_to_binary(["Unknown tool: ", ToolName])}.

%%% Output formatters

format_matches([]) ->
    "No matches found.\n";
format_matches(Matches) ->
    Lines = lists:map(fun(M) ->
        Home = maps:get(home_team, M, "?"),
        Away = maps:get(away_team, M, "?"),
        HG = maps:get(home_goal, M, 0),
        AG = maps:get(away_goal, M, 0),
        {Y, Mo, D} = maps:get(date, M, {0,0,0}),
        Season = maps:get(season, M, 0),
        Comp = maps:get(competition, M, maps:get(tournament, M, "")),
        io_lib:format("~4..0w-~2..0w-~2..0w: ~s ~w-~w ~s (~s, ~w)~n",
            [Y, Mo, D, Home, HG, AG, Away, Comp, Season])
    end, Matches),
    io_lib:format("Found ~w match(es):~n", [length(Matches)]) ++ lists:flatten(Lines).

format_players([]) ->
    "No players found.\n";
format_players(Players) ->
    Lines = lists:zipwith(fun(N, P) ->
        io_lib:format("~w. ~s - Overall: ~w, Position: ~s, Club: ~s, Nationality: ~s~n",
            [N, maps:get(name, P, "?"), maps:get(overall, P, 0),
             maps:get(position, P, "?"), maps:get(club, P, "?"),
             maps:get(nationality, P, "?")])
    end, lists:seq(1, length(Players)), Players),
    lists:flatten(Lines).

format_standings([]) ->
    "No standings data.\n";
format_standings(Standings) ->
    Lines = lists:zipwith(fun(N, {Team, Points, W, D, L}) ->
        io_lib:format("~w. ~s - ~w pts (~wW, ~wD, ~wL)~n",
            [N, Team, Points, W, D, L])
    end, lists:seq(1, length(Standings)), Standings),
    lists:flatten(Lines).

format_team_stats(Team, Season, Comp, Stats) ->
    Matches = maps:get(matches, Stats, 0),
    Wins = maps:get(wins, Stats, 0),
    Draws = maps:get(draws, Stats, 0),
    Losses = maps:get(losses, Stats, 0),
    GF = maps:get(goals_for, Stats, 0),
    GA = maps:get(goals_against, Stats, 0),
    WinRate = if Matches > 0 -> Wins * 100 / Matches; true -> 0 end,
    SeasonStr = if Season > 0 -> integer_to_list(Season); true -> "all seasons" end,
    io_lib:format("~s stats (~s, ~s):~n- Matches: ~w~n- Wins: ~w, Draws: ~w, Losses: ~w~n- Goals For: ~w, Against: ~w~n- Win rate: ~.1f%~n",
        [Team, Comp, SeasonStr, Matches, Wins, Draws, Losses, GF, GA, WinRate]).

format_h2h(T1, T2, R) ->
    Total = maps:get(total, R, 0),
    W1 = maps:get(team1_wins, R, 0),
    W2 = maps:get(team2_wins, R, 0),
    D = maps:get(draws, R, 0),
    io_lib:format("~s vs ~s head-to-head:~n- Total matches: ~w~n- ~s wins: ~w~n- ~s wins: ~w~n- Draws: ~w~n",
        [T1, T2, Total, T1, W1, T2, W2, D]).

%%% STDIO MCP server loop

start() ->
    io:setopts([{encoding, utf8}]),
    State = br_soccer_data:load_all(?DATA_DIR),
    loop(State).

loop(State) ->
    case io:get_line("") of
        eof -> ok;
        {error, _} -> ok;
        Line ->
            Trimmed = string:trim(Line),
            case Trimmed of
                "" -> loop(State);
                _ ->
                    try
                        Req = decode_json(Trimmed),
                        case handle_request(Req, State) of
                            notification -> ok;
                            Resp ->
                                io:put_chars(encode_json(Resp) ++ "\n")
                        end
                    catch
                        _:_ ->
                            Err = #{<<"jsonrpc">> => <<"2.0">>, <<"id">> => null,
                                    <<"error">> => #{<<"code">> => -32700,
                                                     <<"message">> => <<"Parse error">>}},
                            io:put_chars(encode_json(Err) ++ "\n")
                    end,
                    loop(State)
            end
    end.
