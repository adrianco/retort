-module(bsm_mcp_server).
-export([start/0, loop/0, tool_definitions_test/0, call_tool_test/2, handle_message_test/1]).

-define(PROTOCOL_VERSION, <<"2024-11-05">>).
-define(SERVER_NAME, <<"brazilian-soccer-mcp">>).
-define(SERVER_VERSION, <<"1.0.0">>).

start() ->
    ok = bsm_data:load_all(),
    loop().

loop() ->
    case io:get_line("") of
        eof -> ok;
        {error, _} -> ok;
        Line ->
            LineBin = if
                is_binary(Line) -> Line;
                is_list(Line) -> iolist_to_binary(Line)
            end,
            Trimmed = string:trim(LineBin),
            case Trimmed of
                <<>> -> loop();
                _ ->
                    case thoas:decode(Trimmed) of
                        {ok, Msg} ->
                            handle_message(Msg);
                        {error, _} ->
                            ok
                    end,
                    loop()
            end
    end.

handle_message(#{<<"method">> := Method} = Msg) ->
    Id = maps:get(<<"id">>, Msg, null),
    Params = maps:get(<<"params">>, Msg, #{}),
    case Method of
        <<"initialize">> ->
            send_response(Id, initialize_result(Params));
        <<"notifications/initialized">> ->
            ok;
        <<"tools/list">> ->
            send_response(Id, #{<<"tools">> => tool_definitions()});
        <<"tools/call">> ->
            ToolName = maps:get(<<"name">>, Params, <<>>),
            ToolArgs = maps:get(<<"arguments">>, Params, #{}),
            Result = call_tool(ToolName, ToolArgs),
            send_response(Id, Result);
        <<"ping">> ->
            send_response(Id, #{});
        _ ->
            send_error(Id, -32601, <<"Method not found">>, Method)
    end;
handle_message(Msg) ->
    Id = maps:get(<<"id">>, Msg, null),
    send_error(Id, -32600, <<"Invalid Request">>, null).

initialize_result(_Params) ->
    #{
        <<"protocolVersion">> => ?PROTOCOL_VERSION,
        <<"capabilities">> => #{
            <<"tools">> => #{<<"listChanged">> => false}
        },
        <<"serverInfo">> => #{
            <<"name">> => ?SERVER_NAME,
            <<"version">> => ?SERVER_VERSION
        }
    }.

send_response(null, _Result) -> ok;
send_response(Id, Result) ->
    Msg = #{
        <<"jsonrpc">> => <<"2.0">>,
        <<"id">> => Id,
        <<"result">> => Result
    },
    output_json(Msg).

send_error(null, _Code, _Msg, _Data) -> ok;
send_error(Id, Code, Message, Data) ->
    Err = case Data of
        null -> #{<<"code">> => Code, <<"message">> => Message};
        _ -> #{<<"code">> => Code, <<"message">> => Message, <<"data">> => Data}
    end,
    Msg = #{
        <<"jsonrpc">> => <<"2.0">>,
        <<"id">> => Id,
        <<"error">> => Err
    },
    output_json(Msg).

output_json(Msg) ->
    Json = thoas:encode(Msg),
    io:put_chars(standard_io, [Json, "\n"]).

%% ===================================================================
%% Tool definitions
%% ===================================================================
tool_definitions() ->
    [
        #{
            <<"name">> => <<"search_matches">>,
            <<"description">> => <<"Search for soccer matches by team, competition, season, or date range. Returns match results from Brasileirao Serie A, Copa do Brasil, Copa Libertadores, and historical datasets.">>,
            <<"inputSchema">> => #{
                <<"type">> => <<"object">>,
                <<"properties">> => #{
                    <<"team">> => #{<<"type">> => <<"string">>, <<"description">> => <<"Team name (home or away)">>},
                    <<"home_team">> => #{<<"type">> => <<"string">>, <<"description">> => <<"Home team name">>},
                    <<"away_team">> => #{<<"type">> => <<"string">>, <<"description">> => <<"Away team name">>},
                    <<"competition">> => #{<<"type">> => <<"string">>, <<"description">> => <<"Competition: all, brasileirao, copa_brasil, libertadores">>, <<"default">> => <<"all">>},
                    <<"season">> => #{<<"type">> => <<"integer">>, <<"description">> => <<"Season year (e.g. 2023)">>},
                    <<"date_from">> => #{<<"type">> => <<"string">>, <<"description">> => <<"Start date YYYY-MM-DD">>},
                    <<"date_to">> => #{<<"type">> => <<"string">>, <<"description">> => <<"End date YYYY-MM-DD">>},
                    <<"limit">> => #{<<"type">> => <<"integer">>, <<"description">> => <<"Max results (default 20)">>}
                }
            }
        },
        #{
            <<"name">> => <<"get_team_stats">>,
            <<"description">> => <<"Get win/loss/draw statistics for a team, including home and away breakdowns.">>,
            <<"inputSchema">> => #{
                <<"type">> => <<"object">>,
                <<"properties">> => #{
                    <<"team">> => #{<<"type">> => <<"string">>, <<"description">> => <<"Team name">>},
                    <<"competition">> => #{<<"type">> => <<"string">>, <<"description">> => <<"Competition: all, brasileirao, copa_brasil, libertadores">>},
                    <<"season">> => #{<<"type">> => <<"integer">>, <<"description">> => <<"Season year">>}
                },
                <<"required">> => [<<"team">>]
            }
        },
        #{
            <<"name">> => <<"head_to_head">>,
            <<"description">> => <<"Compare two teams head-to-head, showing match history and win/draw/loss record.">>,
            <<"inputSchema">> => #{
                <<"type">> => <<"object">>,
                <<"properties">> => #{
                    <<"team1">> => #{<<"type">> => <<"string">>, <<"description">> => <<"First team">>},
                    <<"team2">> => #{<<"type">> => <<"string">>, <<"description">> => <<"Second team">>},
                    <<"competition">> => #{<<"type">> => <<"string">>, <<"description">> => <<"Filter by competition">>},
                    <<"season">> => #{<<"type">> => <<"integer">>, <<"description">> => <<"Filter by season">>},
                    <<"limit">> => #{<<"type">> => <<"integer">>, <<"description">> => <<"Max matches to return">>}
                },
                <<"required">> => [<<"team1">>, <<"team2">>]
            }
        },
        #{
            <<"name">> => <<"search_players">>,
            <<"description">> => <<"Search FIFA player database by name, nationality, club, or position.">>,
            <<"inputSchema">> => #{
                <<"type">> => <<"object">>,
                <<"properties">> => #{
                    <<"name">> => #{<<"type">> => <<"string">>, <<"description">> => <<"Player name (partial match)">>},
                    <<"nationality">> => #{<<"type">> => <<"string">>, <<"description">> => <<"Player nationality (e.g. Brazil)">>},
                    <<"club">> => #{<<"type">> => <<"string">>, <<"description">> => <<"Club name (e.g. Flamengo)">>},
                    <<"position">> => #{<<"type">> => <<"string">>, <<"description">> => <<"Position (GK, CB, LW, ST, etc.)">>},
                    <<"min_rating">> => #{<<"type">> => <<"integer">>, <<"description">> => <<"Minimum overall rating">>},
                    <<"max_results">> => #{<<"type">> => <<"integer">>, <<"description">> => <<"Max results (default 20)">>}
                }
            }
        },
        #{
            <<"name">> => <<"get_standings">>,
            <<"description">> => <<"Calculate league standings for a given season based on match results.">>,
            <<"inputSchema">> => #{
                <<"type">> => <<"object">>,
                <<"properties">> => #{
                    <<"season">> => #{<<"type">> => <<"integer">>, <<"description">> => <<"Season year">>},
                    <<"competition">> => #{<<"type">> => <<"string">>, <<"description">> => <<"Competition: brasileirao, copa_brasil, libertadores">>, <<"default">> => <<"brasileirao">>}
                },
                <<"required">> => [<<"season">>]
            }
        },
        #{
            <<"name">> => <<"get_biggest_wins">>,
            <<"description">> => <<"Find the biggest victories (largest goal margin) in the dataset.">>,
            <<"inputSchema">> => #{
                <<"type">> => <<"object">>,
                <<"properties">> => #{
                    <<"competition">> => #{<<"type">> => <<"string">>, <<"description">> => <<"Competition filter">>},
                    <<"season">> => #{<<"type">> => <<"integer">>, <<"description">> => <<"Season filter">>},
                    <<"limit">> => #{<<"type">> => <<"integer">>, <<"description">> => <<"Number of results (default 10)">>}
                }
            }
        },
        #{
            <<"name">> => <<"get_season_summary">>,
            <<"description">> => <<"Get overall statistics for a season: total goals, home win rate, averages.">>,
            <<"inputSchema">> => #{
                <<"type">> => <<"object">>,
                <<"properties">> => #{
                    <<"season">> => #{<<"type">> => <<"integer">>, <<"description">> => <<"Season year">>},
                    <<"competition">> => #{<<"type">> => <<"string">>, <<"description">> => <<"Competition filter">>}
                },
                <<"required">> => [<<"season">>]
            }
        },
        #{
            <<"name">> => <<"get_competition_matches">>,
            <<"description">> => <<"List matches in a competition, optionally filtered by season or stage.">>,
            <<"inputSchema">> => #{
                <<"type">> => <<"object">>,
                <<"properties">> => #{
                    <<"competition">> => #{<<"type">> => <<"string">>, <<"description">> => <<"Competition: brasileirao, copa_brasil, libertadores">>},
                    <<"season">> => #{<<"type">> => <<"integer">>, <<"description">> => <<"Season year">>},
                    <<"stage">> => #{<<"type">> => <<"string">>, <<"description">> => <<"Stage (e.g. final, group stage)">>},
                    <<"limit">> => #{<<"type">> => <<"integer">>, <<"description">> => <<"Max results (default 50)">>}
                }
            }
        }
    ].

%% ===================================================================
%% Tool dispatch
%% ===================================================================
call_tool(<<"search_matches">>, Args) ->
    try
        Result = bsm_query:search_matches(Args),
        make_text_result(format_search_matches(Result))
    catch E:R:ST ->
        make_error_result(io_lib:format("Error: ~p:~p~n~p", [E, R, ST]))
    end;
call_tool(<<"get_team_stats">>, Args) ->
    try
        Result = bsm_query:get_team_stats(Args),
        make_text_result(format_team_stats(Result))
    catch E:R:ST ->
        make_error_result(io_lib:format("Error: ~p:~p~n~p", [E, R, ST]))
    end;
call_tool(<<"head_to_head">>, Args) ->
    try
        Result = bsm_query:head_to_head(Args),
        make_text_result(format_head_to_head(Result))
    catch E:R:ST ->
        make_error_result(io_lib:format("Error: ~p:~p~n~p", [E, R, ST]))
    end;
call_tool(<<"search_players">>, Args) ->
    try
        Result = bsm_query:search_players(Args),
        make_text_result(format_players(Result))
    catch E:R:ST ->
        make_error_result(io_lib:format("Error: ~p:~p~n~p", [E, R, ST]))
    end;
call_tool(<<"get_standings">>, Args) ->
    try
        Result = bsm_query:get_standings(Args),
        make_text_result(format_standings(Result))
    catch E:R:ST ->
        make_error_result(io_lib:format("Error: ~p:~p~n~p", [E, R, ST]))
    end;
call_tool(<<"get_biggest_wins">>, Args) ->
    try
        Result = bsm_query:get_biggest_wins(Args),
        make_text_result(format_biggest_wins(Result))
    catch E:R:ST ->
        make_error_result(io_lib:format("Error: ~p:~p~n~p", [E, R, ST]))
    end;
call_tool(<<"get_season_summary">>, Args) ->
    try
        Result = bsm_query:get_season_summary(Args),
        make_text_result(format_season_summary(Result))
    catch E:R:ST ->
        make_error_result(io_lib:format("Error: ~p:~p~n~p", [E, R, ST]))
    end;
call_tool(<<"get_competition_matches">>, Args) ->
    try
        Result = bsm_query:get_competition_matches(Args),
        make_text_result(format_search_matches(Result))
    catch E:R:ST ->
        make_error_result(io_lib:format("Error: ~p:~p~n~p", [E, R, ST]))
    end;
call_tool(Unknown, _Args) ->
    make_error_result(io_lib:format("Unknown tool: ~s", [Unknown])).

make_text_result(Text) ->
    #{
        <<"content">> => [#{<<"type">> => <<"text">>, <<"text">> => iolist_to_binary(Text)}]
    }.

make_error_result(Text) ->
    #{
        <<"content">> => [#{<<"type">> => <<"text">>, <<"text">> => iolist_to_binary(Text)}],
        <<"isError">> => true
    }.

%% ===================================================================
%% Formatters
%% ===================================================================
format_search_matches(#{total := Total, showing := Showing, matches := Matches}) ->
    Header = io_lib:format("Found ~p matches (showing ~p):\n\n", [Total, Showing]),
    Rows = [format_match_row(M) || M <- Matches],
    [Header | Rows].

format_match_row(M) ->
    Date = maps:get(date, M, maps:get(<<"date">>, M, <<>>)),
    HT = maps:get(home_team, M, maps:get(<<"home_team">>, M, <<>>)),
    AT = maps:get(away_team, M, maps:get(<<"away_team">>, M, <<>>)),
    HG = maps:get(home_goal, M, maps:get(<<"home_goal">>, M, 0)),
    AG = maps:get(away_goal, M, maps:get(<<"away_goal">>, M, 0)),
    Comp = maps:get(competition, M, maps:get(<<"competition">>, M, <<>>)),
    Round = maps:get(round, M, maps:get(<<"round">>, M, <<>>)),
    Stage = maps:get(stage, M, maps:get(<<"stage">>, M, <<>>)),
    Season = maps:get(season, M, maps:get(<<"season">>, M, 0)),
    Extra = case {Round, Stage} of
        {<<>>, <<>>} -> io_lib:format("~p", [Season]);
        {R, <<>>} when R =/= <<>> -> io_lib:format("~p Round ~s", [Season, R]);
        {<<>>, S} when S =/= <<>> -> io_lib:format("~p ~s", [Season, S]);
        {R, S} -> io_lib:format("~p ~s ~s", [Season, R, S])
    end,
    io_lib:format("- ~s: ~s ~p-~p ~s (~s ~s)\n",
        [Date, HT, HG, AG, AT, comp_name(Comp), Extra]).

comp_name(<<"brasileirao">>) -> "Brasileirao Serie A";
comp_name(<<"brasileirao_hist">>) -> "Brasileirao (hist)";
comp_name(<<"copa_brasil">>) -> "Copa do Brasil";
comp_name(<<"libertadores">>) -> "Copa Libertadores";
comp_name(<<"stats">>) -> "BR Football";
comp_name(X) when is_binary(X) -> binary_to_list(X);
comp_name(X) -> X.

format_team_stats(R) ->
    Team = maps:get(team, R, <<>>),
    Comp = maps:get(competition, R, <<>>),
    Season = maps:get(season, R, 0),
    Played = maps:get(total_matches, R, 0),
    W = maps:get(wins, R, 0),
    D = maps:get(draws, R, 0),
    L = maps:get(losses, R, 0),
    GF = maps:get(goals_for, R, 0),
    GA = maps:get(goals_against, R, 0),
    GD = maps:get(goal_diff, R, 0),
    WR = maps:get(win_rate, R, 0.0),
    Home = maps:get(home, R, #{}),
    Away = maps:get(away, R, #{}),
    SeasonStr = case Season of 0 -> "All seasons"; _ -> integer_to_list(Season) end,
    CompStr = case Comp of <<"all">> -> "all competitions"; _ -> comp_name(Comp) end,
    io_lib:format(
        "~s - ~s (~s):\n"
        "  Played: ~p | W: ~p D: ~p L: ~p\n"
        "  Goals For: ~p | Goals Against: ~p | GD: ~p\n"
        "  Win rate: ~p%\n"
        "  Home: ~pP ~pW ~pD ~pL (GF:~p GA:~p)\n"
        "  Away: ~pP ~pW ~pD ~pL (GF:~p GA:~p)\n",
        [Team, SeasonStr, CompStr,
         Played, W, D, L, GF, GA, GD, WR,
         maps:get(played, Home, 0), maps:get(wins, Home, 0),
         maps:get(draws, Home, 0), maps:get(losses, Home, 0),
         maps:get(goals_for, Home, 0), maps:get(goals_against, Home, 0),
         maps:get(played, Away, 0), maps:get(wins, Away, 0),
         maps:get(draws, Away, 0), maps:get(losses, Away, 0),
         maps:get(goals_for, Away, 0), maps:get(goals_against, Away, 0)
        ]).

format_head_to_head(R) ->
    T1 = maps:get(team1, R, <<>>),
    T2 = maps:get(team2, R, <<>>),
    Total = maps:get(total_matches, R, 0),
    T1W = maps:get(team1_wins, R, 0),
    T2W = maps:get(team2_wins, R, 0),
    Draws = maps:get(draws, R, 0),
    Matches = maps:get(matches, R, []),
    Header = io_lib:format(
        "Head-to-head: ~s vs ~s\n"
        "Total matches: ~p\n"
        "~s wins: ~p | ~s wins: ~p | Draws: ~p\n\n"
        "Recent matches:\n",
        [T1, T2, Total, T1, T1W, T2, T2W, Draws]),
    Rows = [format_match_row(M) || M <- Matches],
    [Header | Rows].

format_players(#{total := Total, showing := Showing, players := Players}) ->
    Header = io_lib:format("Found ~p players (showing ~p):\n\n", [Total, Showing]),
    Rows = lists:zipwith(fun(I, P) ->
        Name = maps:get(name, P, <<>>),
        Nat = maps:get(nationality, P, <<>>),
        Club = maps:get(club, P, <<>>),
        Pos = maps:get(position, P, <<>>),
        Rating = maps:get(overall, P, 0),
        Pot = maps:get(potential, P, 0),
        Age = maps:get(age, P, 0),
        io_lib:format("~p. ~s | ~s | ~s | ~s | Overall: ~p | Potential: ~p | Age: ~p\n",
            [I, Name, Nat, Club, Pos, Rating, Pot, Age])
    end, lists:seq(1, length(Players)), Players),
    [Header | Rows].

format_standings(#{season := Season, competition := Comp, standings := Standings, total_matches := TM}) ->
    SeasonStr = case Season of 0 -> "All"; _ -> integer_to_list(Season) end,
    Header = io_lib:format("~s ~s Standings (~p matches):\n\n",
        [SeasonStr, comp_name(Comp), TM]),
    Rows = [format_standing_row(S) || S <- Standings],
    [Header | Rows].

format_standing_row(S) ->
    Pos = maps:get(position, S, 0),
    Team = maps:get(team, S, <<>>),
    Pts = maps:get(points, S, 0),
    W = maps:get(wins, S, 0),
    D = maps:get(draws, S, 0),
    L = maps:get(losses, S, 0),
    GF = maps:get(goals_for, S, 0),
    GA = maps:get(goals_against, S, 0),
    GD = maps:get(goal_diff, S, 0),
    Played = maps:get(played, S, 0),
    io_lib:format("~2p. ~-30s ~3p pts | ~2pP ~2pW ~2pD ~2pL | GF:~2p GA:~2p GD:~3p\n",
        [Pos, Team, Pts, Played, W, D, L, GF, GA, GD]).

format_biggest_wins(#{competition := Comp, season := Season, biggest_wins := Wins}) ->
    CompStr = comp_name(Comp),
    SeasonStr = case Season of 0 -> "All seasons"; _ -> integer_to_list(Season) end,
    Header = io_lib:format("Biggest wins in ~s (~s):\n\n", [CompStr, SeasonStr]),
    Rows = lists:zipwith(fun(I, M) ->
        Date = maps:get(date, M, maps:get(<<"date">>, M, <<>>)),
        HT = maps:get(home_team, M, maps:get(<<"home_team">>, M, <<>>)),
        AT = maps:get(away_team, M, maps:get(<<"away_team">>, M, <<>>)),
        HG = maps:get(home_goal, M, 0),
        AG = maps:get(away_goal, M, 0),
        io_lib:format("~p. ~s: ~s ~p-~p ~s\n", [I, Date, HT, HG, AG, AT])
    end, lists:seq(1, length(Wins)), Wins),
    [Header | Rows].

format_season_summary(R) ->
    Season = maps:get(season, R, 0),
    Comp = maps:get(competition, R, <<>>),
    TM = maps:get(total_matches, R, 0),
    TG = maps:get(total_goals, R, 0),
    Avg = maps:get(avg_goals_per_match, R, 0.0),
    HW = maps:get(home_wins, R, 0),
    AW = maps:get(away_wins, R, 0),
    Dr = maps:get(draws, R, 0),
    HWR = maps:get(home_win_rate, R, 0.0),
    SeasonStr = case Season of 0 -> "All seasons"; _ -> integer_to_list(Season) end,
    io_lib:format(
        "~s ~s Summary:\n"
        "  Total matches: ~p\n"
        "  Total goals: ~p\n"
        "  Avg goals/match: ~p\n"
        "  Home wins: ~p (~p%) | Away wins: ~p | Draws: ~p\n",
        [SeasonStr, comp_name(Comp), TM, TG, Avg, HW, HWR, AW, Dr]).

%% ===================================================================
%% Test-friendly exports (wrap internal functions without I/O side effects)
%% ===================================================================
tool_definitions_test() ->
    tool_definitions().

call_tool_test(Name, Args) ->
    call_tool(Name, Args).

handle_message_test(Msg) ->
    #{<<"method">> := Method} = Msg,
    Id = maps:get(<<"id">>, Msg, 1),
    Params = maps:get(<<"params">>, Msg, #{}),
    Result = case Method of
        <<"initialize">> -> initialize_result(Params);
        <<"tools/list">> -> #{<<"tools">> => tool_definitions()};
        <<"tools/call">> ->
            ToolName = maps:get(<<"name">>, Params, <<>>),
            ToolArgs = maps:get(<<"arguments">>, Params, #{}),
            call_tool(ToolName, ToolArgs);
        _ -> #{<<"error">> => <<"unknown">>}
    end,
    #{<<"jsonrpc">> => <<"2.0">>, <<"id">> => Id, <<"result">> => Result}.
