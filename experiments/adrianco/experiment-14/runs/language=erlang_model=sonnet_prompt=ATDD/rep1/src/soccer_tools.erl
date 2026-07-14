%% MCP tool definitions and dispatch for the Brazilian Soccer MCP server.
-module(soccer_tools).
-export([list/0, call/2]).

%%--------------------------------------------------------------------
%% Tool Definitions
%%--------------------------------------------------------------------

list() ->
    [
        #{
            <<"name">> => <<"find_matches">>,
            <<"description">> => <<"Find soccer matches by team, competition, season, or date range. Searches across Brasileirao, Copa do Brasil, Copa Libertadores, and historical datasets.">>,
            <<"inputSchema">> => #{
                <<"type">> => <<"object">>,
                <<"properties">> => #{
                    <<"team">>        => #{<<"type">> => <<"string">>, <<"description">> => <<"Team name (partial, case-insensitive). Matches home or away.">>},
                    <<"competition">> => #{<<"type">> => <<"string">>, <<"description">> => <<"Competition: brasileirao, copa_do_brasil, libertadores, novo_brasileiro">>},
                    <<"season">>      => #{<<"type">> => <<"integer">>, <<"description">> => <<"Season year e.g. 2023">>},
                    <<"date_from">>   => #{<<"type">> => <<"string">>, <<"description">> => <<"Start date YYYY-MM-DD">>},
                    <<"date_to">>     => #{<<"type">> => <<"string">>, <<"description">> => <<"End date YYYY-MM-DD">>},
                    <<"limit">>       => #{<<"type">> => <<"integer">>, <<"description">> => <<"Max results (default 20)">>}
                }
            }
        },
        #{
            <<"name">> => <<"get_team_stats">>,
            <<"description">> => <<"Get win/draw/loss statistics for a team, with home/away breakdown, optionally filtered by competition and season.">>,
            <<"inputSchema">> => #{
                <<"type">> => <<"object">>,
                <<"required">> => [<<"team">>],
                <<"properties">> => #{
                    <<"team">>        => #{<<"type">> => <<"string">>, <<"description">> => <<"Team name">>},
                    <<"competition">> => #{<<"type">> => <<"string">>, <<"description">> => <<"Competition filter">>},
                    <<"season">>      => #{<<"type">> => <<"integer">>, <<"description">> => <<"Season year filter">>}
                }
            }
        },
        #{
            <<"name">> => <<"find_players">>,
            <<"description">> => <<"Search the FIFA player database by name, nationality, club, position, or minimum rating. Results sorted by overall rating.">>,
            <<"inputSchema">> => #{
                <<"type">> => <<"object">>,
                <<"properties">> => #{
                    <<"name">>        => #{<<"type">> => <<"string">>, <<"description">> => <<"Player name (partial match)">>},
                    <<"nationality">> => #{<<"type">> => <<"string">>, <<"description">> => <<"Nationality e.g. Brazil">>},
                    <<"club">>        => #{<<"type">> => <<"string">>, <<"description">> => <<"Club name (partial match)">>},
                    <<"position">>    => #{<<"type">> => <<"string">>, <<"description">> => <<"Position e.g. GK, ST, LW">>},
                    <<"min_rating">>  => #{<<"type">> => <<"integer">>, <<"description">> => <<"Minimum overall rating">>},
                    <<"limit">>       => #{<<"type">> => <<"integer">>, <<"description">> => <<"Max results (default 20)">>}
                }
            }
        },
        #{
            <<"name">> => <<"get_head_to_head">>,
            <<"description">> => <<"Get the head-to-head record between two teams across all available match data.">>,
            <<"inputSchema">> => #{
                <<"type">> => <<"object">>,
                <<"required">> => [<<"team1">>, <<"team2">>],
                <<"properties">> => #{
                    <<"team1">>       => #{<<"type">> => <<"string">>, <<"description">> => <<"First team name">>},
                    <<"team2">>       => #{<<"type">> => <<"string">>, <<"description">> => <<"Second team name">>},
                    <<"competition">> => #{<<"type">> => <<"string">>, <<"description">> => <<"Competition filter">>},
                    <<"season">>      => #{<<"type">> => <<"integer">>, <<"description">> => <<"Season filter">>}
                }
            }
        },
        #{
            <<"name">> => <<"get_standings">>,
            <<"description">> => <<"Calculate final standings for a competition season from match results. Points: 3 for win, 1 for draw.">>,
            <<"inputSchema">> => #{
                <<"type">> => <<"object">>,
                <<"required">> => [<<"season">>],
                <<"properties">> => #{
                    <<"competition">> => #{<<"type">> => <<"string">>, <<"description">> => <<"Competition (default: brasileirao)">>},
                    <<"season">>      => #{<<"type">> => <<"integer">>, <<"description">> => <<"Season year">>}
                }
            }
        },
        #{
            <<"name">> => <<"get_statistics">>,
            <<"description">> => <<"Get aggregated statistics across matches: biggest_wins, avg_goals, or home_away_rates.">>,
            <<"inputSchema">> => #{
                <<"type">> => <<"object">>,
                <<"required">> => [<<"stat_type">>],
                <<"properties">> => #{
                    <<"stat_type">>   => #{<<"type">> => <<"string">>, <<"description">> => <<"Type: biggest_wins, avg_goals, home_away_rates">>},
                    <<"competition">> => #{<<"type">> => <<"string">>, <<"description">> => <<"Competition filter">>},
                    <<"season">>      => #{<<"type">> => <<"integer">>, <<"description">> => <<"Season filter">>},
                    <<"limit">>       => #{<<"type">> => <<"integer">>, <<"description">> => <<"Max results for list types (default 10)">>}
                }
            }
        }
    ].

%%--------------------------------------------------------------------
%% Tool Dispatch
%%--------------------------------------------------------------------

call(<<"find_matches">>, Args) ->
    Criteria = args_to_match_criteria(Args),
    AllMatches = soccer_data:find_matches_all(Criteria),
    Sorted = lists:sort(fun(A, B) ->
        maps:get(date, A, <<>>) >= maps:get(date, B, <<>>)
    end, AllMatches),
    Limit = soccer_data:to_integer(maps:get(<<"limit">>, Args, 20)),
    Shown = lists:sublist(Sorted, Limit),
    Result = #{
        <<"total_found">> => length(AllMatches),
        <<"showing">>     => length(Shown),
        <<"matches">>     => [soccer_data:format_match(M) || M <- Shown]
    },
    {ok, iolist_to_binary(json:encode(Result))};

call(<<"get_team_stats">>, Args) ->
    Team = maps:get(<<"team">>, Args, <<>>),
    Criteria = args_to_match_criteria(maps:remove(<<"team">>, Args)),
    AllMatches = soccer_data:find_matches_all(Criteria#{team => Team}),
    Stats = soccer_data:compute_team_stats(Team, AllMatches),
    Result = #{
        <<"team">>           => Team,
        <<"competition">>    => maps:get(<<"competition">>, Args, <<"all">>),
        <<"season">>         => maps:get(<<"season">>, Args, <<"all">>),
        <<"matches_played">> => maps:get(played, Stats, 0),
        <<"wins">>           => maps:get(wins, Stats, 0),
        <<"draws">>          => maps:get(draws, Stats, 0),
        <<"losses">>         => maps:get(losses, Stats, 0),
        <<"goals_for">>      => maps:get(goals_for, Stats, 0),
        <<"goals_against">>  => maps:get(goals_against, Stats, 0),
        <<"goal_difference">> => maps:get(goals_for, Stats, 0) - maps:get(goals_against, Stats, 0),
        <<"points">>         => maps:get(points, Stats, 0),
        <<"win_rate">>       => maps:get(win_rate, Stats, 0.0),
        <<"home_record">>    => #{
            <<"wins">>   => maps:get(home_wins, Stats, 0),
            <<"draws">>  => maps:get(home_draws, Stats, 0),
            <<"losses">> => maps:get(home_losses, Stats, 0)
        },
        <<"away_record">>    => #{
            <<"wins">>   => maps:get(away_wins, Stats, 0),
            <<"draws">>  => maps:get(away_draws, Stats, 0),
            <<"losses">> => maps:get(away_losses, Stats, 0)
        }
    },
    {ok, iolist_to_binary(json:encode(Result))};

call(<<"find_players">>, Args) ->
    Criteria = args_to_player_criteria(Args),
    AllPlayers = soccer_data:find_players_all(Criteria),
    TotalFound = length(AllPlayers),
    Limit = soccer_data:to_integer(maps:get(<<"limit">>, Args, 20)),
    Shown = lists:sublist(AllPlayers, Limit),
    Result = #{
        <<"total_found">> => TotalFound,
        <<"showing">>     => length(Shown),
        <<"players">>     => [soccer_data:format_player(P) || P <- Shown]
    },
    {ok, iolist_to_binary(json:encode(Result))};

call(<<"get_head_to_head">>, Args) ->
    Team1 = maps:get(<<"team1">>, Args, <<>>),
    Team2 = maps:get(<<"team2">>, Args, <<>>),
    Criteria = args_to_match_criteria(maps:without([<<"team1">>, <<"team2">>], Args)),
    H2H = soccer_data:get_head_to_head(Team1, Team2, Criteria),
    Result = #{
        <<"team1">>          => maps:get(team1, H2H),
        <<"team2">>          => maps:get(team2, H2H),
        <<"total_matches">>  => maps:get(total_matches, H2H),
        <<"team1_wins">>     => maps:get(team1_wins, H2H),
        <<"team2_wins">>     => maps:get(team2_wins, H2H),
        <<"draws">>          => maps:get(draws, H2H),
        <<"team1_goals">>    => maps:get(team1_goals, H2H),
        <<"team2_goals">>    => maps:get(team2_goals, H2H),
        <<"recent_matches">> => maps:get(recent_matches, H2H)
    },
    {ok, iolist_to_binary(json:encode(Result))};

call(<<"get_standings">>, Args) ->
    Competition = maps:get(<<"competition">>, Args, <<"brasileirao">>),
    Season = soccer_data:to_integer(maps:get(<<"season">>, Args, 0)),
    Standings = soccer_data:get_standings(Competition, Season),
    Result = #{
        <<"competition">> => Competition,
        <<"season">>      => Season,
        <<"standings">>   => [soccer_data:format_standing(S) || S <- Standings]
    },
    {ok, iolist_to_binary(json:encode(Result))};

call(<<"get_statistics">>, Args) ->
    StatType = maps:get(<<"stat_type">>, Args, <<"avg_goals">>),
    Criteria = args_to_match_criteria(maps:without([<<"stat_type">>], Args)),
    case StatType of
        <<"biggest_wins">> ->
            Results = soccer_data:stats_biggest_wins(Criteria),
            Result = #{<<"stat_type">> => StatType, <<"results">> => Results},
            {ok, iolist_to_binary(json:encode(Result))};
        _ ->
            Stats = soccer_data:stats_avg_goals(Criteria),
            Result = #{
                <<"stat_type">>           => StatType,
                <<"total_matches">>       => maps:get(total_matches, Stats, 0),
                <<"total_goals">>         => maps:get(total_goals, Stats, 0),
                <<"avg_goals_per_match">> => maps:get(avg_goals_per_match, Stats, 0.0),
                <<"home_wins">>           => maps:get(home_wins, Stats, 0),
                <<"away_wins">>           => maps:get(away_wins, Stats, 0),
                <<"draws">>               => maps:get(draws, Stats, 0),
                <<"home_win_rate">>       => maps:get(home_win_rate, Stats, 0.0),
                <<"away_win_rate">>       => maps:get(away_win_rate, Stats, 0.0),
                <<"draw_rate">>           => maps:get(draw_rate, Stats, 0.0)
            },
            {ok, iolist_to_binary(json:encode(Result))}
    end;

call(Unknown, _Args) ->
    {error, <<"Unknown tool: ", Unknown/binary>>}.

%%--------------------------------------------------------------------
%% Argument Conversion Helpers
%%--------------------------------------------------------------------

args_to_match_criteria(Args) ->
    Fields = [
        {<<"team">>,        team,        fun(V) -> V end},
        {<<"competition">>, competition, fun(V) -> V end},
        {<<"season">>,      season,      fun(V) -> soccer_data:to_integer(V) end},
        {<<"date_from">>,   date_from,   fun(V) -> V end},
        {<<"date_to">>,     date_to,     fun(V) -> V end},
        {<<"limit">>,       limit,       fun(V) -> soccer_data:to_integer(V) end}
    ],
    from_args(Args, Fields).

args_to_player_criteria(Args) ->
    Fields = [
        {<<"name">>,        name,        fun(V) -> V end},
        {<<"nationality">>, nationality, fun(V) -> V end},
        {<<"club">>,        club,        fun(V) -> V end},
        {<<"position">>,    position,    fun(V) -> V end},
        {<<"min_rating">>,  min_rating,  fun(V) -> soccer_data:to_integer(V) end},
        {<<"limit">>,       limit,       fun(V) -> soccer_data:to_integer(V) end}
    ],
    from_args(Args, Fields).

from_args(Args, Fields) ->
    lists:foldl(fun({BinKey, AtomKey, Conv}, Acc) ->
        case maps:find(BinKey, Args) of
            {ok, Value} -> Acc#{AtomKey => Conv(Value)};
            error       -> Acc
        end
    end, #{}, Fields).
