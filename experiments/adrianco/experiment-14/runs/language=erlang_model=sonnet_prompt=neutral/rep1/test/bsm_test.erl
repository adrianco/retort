-module(bsm_test).
-include_lib("eunit/include/eunit.hrl").

%% ===================================================================
%% Setup / Teardown
%% ===================================================================
setup() ->
    application:ensure_all_started(thoas),
    ok = bsm_data:load_all().

%% ===================================================================
%% CSV Parser Tests
%% ===================================================================
csv_parse_test() ->
    %% Simple CSV
    Lines = <<"name,age\nAlice,30\nBob,25">>,
    TmpFile = "/tmp/bsm_test_csv.csv",
    file:write_file(TmpFile, Lines),
    Rows = bsm_csv:parse_file(TmpFile),
    ?assertEqual(2, length(Rows)),
    ?assertEqual(<<"Alice">>, maps:get(<<"name">>, hd(Rows))),
    ?assertEqual(<<"30">>, maps:get(<<"age">>, hd(Rows))).

csv_quoted_test() ->
    Lines = <<"name,team\n\"Neymar Jr\",\"Paris Saint-Germain\"">>,
    TmpFile = "/tmp/bsm_test_csv2.csv",
    file:write_file(TmpFile, Lines),
    [Row] = bsm_csv:parse_file(TmpFile),
    ?assertEqual(<<"Neymar Jr">>, maps:get(<<"name">>, Row)),
    ?assertEqual(<<"Paris Saint-Germain">>, maps:get(<<"team">>, Row)).

csv_bom_test() ->
    Lines = <<16#EF, 16#BB, 16#BF, "col1,col2\nval1,val2">>,
    TmpFile = "/tmp/bsm_test_bom.csv",
    file:write_file(TmpFile, Lines),
    [Row] = bsm_csv:parse_file(TmpFile),
    ?assertEqual(<<"val1">>, maps:get(<<"col1">>, Row)).

%% ===================================================================
%% Data Loading Tests
%% ===================================================================
data_load_test_() ->
    {timeout, 60, fun() ->
        setup(),
        Matches = bsm_data:get_matches(),
        ?assert(length(Matches) > 1000),
        Players = bsm_data:get_players(),
        ?assert(length(Players) > 1000)
    end}.

data_all_files_loaded_test() ->
    setup(),
    Matches = bsm_data:get_matches(),
    %% Check all competition types present
    Comps = lists:usort([maps:get(competition, M) || M <- Matches]),
    ?assert(lists:member(brasileirao, Comps)),
    ?assert(lists:member(copa_brasil, Comps)),
    ?assert(lists:member(libertadores, Comps)),
    ?assert(lists:member(brasileirao_hist, Comps)).

data_match_fields_test() ->
    setup(),
    [M | _] = bsm_data:get_matches(),
    ?assert(maps:is_key(home_team, M)),
    ?assert(maps:is_key(away_team, M)),
    ?assert(maps:is_key(home_goal, M)),
    ?assert(maps:is_key(away_goal, M)),
    ?assert(maps:is_key(season, M)),
    ?assert(maps:is_key(date, M)).

data_player_fields_test() ->
    setup(),
    [P | _] = bsm_data:get_players(),
    ?assert(maps:is_key(name, P)),
    ?assert(maps:is_key(nationality, P)),
    ?assert(maps:is_key(overall, P)),
    ?assert(maps:is_key(club, P)),
    ?assert(maps:is_key(position, P)).

%% ===================================================================
%% Team Name Normalization Tests
%% ===================================================================
team_normalize_test() ->
    %% Should strip state suffix
    ?assertEqual(<<"Palmeiras">>, bsm_data:normalize_team_name(<<"Palmeiras-SP">>)),
    ?assertEqual(<<"Flamengo">>, bsm_data:normalize_team_name(<<"Flamengo-RJ">>)),
    %% Should keep names without suffix unchanged
    ?assertEqual(<<"Palmeiras">>, bsm_data:normalize_team_name(<<"Palmeiras">>)).

%% ===================================================================
%% Query Tests
%% ===================================================================
search_matches_by_team_test() ->
    setup(),
    Result = bsm_query:search_matches(#{<<"team">> => <<"Flamengo">>, <<"limit">> => 50}),
    Total = maps:get(total, Result),
    ?assert(Total > 10),
    Matches = maps:get(matches, Result),
    %% All matches should involve Flamengo
    lists:foreach(fun(M) ->
        HT = string:lowercase(binary_to_list(maps:get(home_team, M))),
        AT = string:lowercase(binary_to_list(maps:get(away_team, M))),
        HasFla = string:find(HT, "flamengo") =/= nomatch orelse
                 string:find(AT, "flamengo") =/= nomatch,
        ?assert(HasFla)
    end, Matches).

search_matches_by_season_test() ->
    setup(),
    Result = bsm_query:search_matches(#{<<"season">> => 2019, <<"competition">> => <<"brasileirao">>, <<"limit">> => 100}),
    Total = maps:get(total, Result),
    ?assert(Total > 0),
    Matches = maps:get(matches, Result),
    lists:foreach(fun(M) ->
        S = maps:get(season, M),
        ?assertEqual(2019, S)
    end, Matches).

search_matches_date_range_test() ->
    setup(),
    Result = bsm_query:search_matches(#{
        <<"date_from">> => <<"2019-01-01">>,
        <<"date_to">> => <<"2019-12-31">>,
        <<"competition">> => <<"brasileirao">>,
        <<"limit">> => 100
    }),
    Total = maps:get(total, Result),
    ?assert(Total > 0).

head_to_head_test() ->
    setup(),
    Result = bsm_query:head_to_head(#{
        <<"team1">> => <<"Flamengo">>,
        <<"team2">> => <<"Fluminense">>,
        <<"limit">> => 30
    }),
    Total = maps:get(total_matches, Result),
    ?assert(Total > 0),
    T1W = maps:get(team1_wins, Result),
    T2W = maps:get(team2_wins, Result),
    Draws = maps:get(draws, Result),
    ?assert(T1W + T2W + Draws =:= Total).

team_stats_test() ->
    setup(),
    Result = bsm_query:get_team_stats(#{
        <<"team">> => <<"Palmeiras">>,
        <<"competition">> => <<"brasileirao">>,
        <<"season">> => 2019
    }),
    Played = maps:get(total_matches, Result),
    ?assert(Played > 0),
    W = maps:get(wins, Result),
    D = maps:get(draws, Result),
    L = maps:get(losses, Result),
    ?assertEqual(Played, W + D + L).

search_players_by_nationality_test_() ->
    {timeout, 30, fun() ->
        setup(),
        Result = bsm_query:search_players(#{
            <<"nationality">> => <<"Brazil">>,
            <<"max_results">> => 50
        }),
        Total = maps:get(total, Result),
        ?assert(Total > 100),
        Players = maps:get(players, Result),
        lists:foreach(fun(P) ->
            Nat = string:lowercase(binary_to_list(maps:get(nationality, P))),
            ?assertEqual("brazil", Nat)
        end, Players)
    end}.

search_players_by_club_test_() ->
    {timeout, 30, fun() ->
        setup(),
        Result = bsm_query:search_players(#{
            <<"club">> => <<"Fluminense">>,
            <<"max_results">> => 20
        }),
        Players = maps:get(players, Result),
        ?assert(length(Players) > 0)
    end}.

search_players_by_name_test_() ->
    {timeout, 30, fun() ->
        setup(),
        Result = bsm_query:search_players(#{
            <<"name">> => <<"Neymar">>,
            <<"max_results">> => 5
        }),
        Players = maps:get(players, Result),
        ?assert(length(Players) > 0),
        [First | _] = Players,
        Name = string:lowercase(binary_to_list(maps:get(name, First))),
        ?assertNotEqual(nomatch, string:find(Name, "neymar"))
    end}.

search_players_min_rating_test_() ->
    {timeout, 30, fun() ->
        setup(),
        Result = bsm_query:search_players(#{
            <<"min_rating">> => 85,
            <<"max_results">> => 50
        }),
        Players = maps:get(players, Result),
        lists:foreach(fun(P) ->
            ?assert(maps:get(overall, P) >= 85)
        end, Players)
    end}.

get_standings_test() ->
    setup(),
    Result = bsm_query:get_standings(#{
        <<"season">> => 2019,
        <<"competition">> => <<"brasileirao">>
    }),
    Standings = maps:get(standings, Result),
    ?assert(length(Standings) > 10),
    [Top | _] = Standings,
    ?assertEqual(1, maps:get(position, Top)),
    ?assert(maps:get(points, Top) > 0).

get_biggest_wins_test() ->
    setup(),
    Result = bsm_query:get_biggest_wins(#{
        <<"competition">> => <<"all">>,
        <<"limit">> => 5
    }),
    Wins = maps:get(biggest_wins, Result),
    ?assertEqual(5, length(Wins)),
    [First | _] = Wins,
    HG = maps:get(home_goal, First),
    AG = maps:get(away_goal, First),
    ?assert(abs(HG - AG) >= 4).

get_season_summary_test() ->
    setup(),
    Result = bsm_query:get_season_summary(#{
        <<"season">> => 2022,
        <<"competition">> => <<"brasileirao">>
    }),
    TM = maps:get(total_matches, Result),
    ?assert(TM > 0),
    HW = maps:get(home_wins, Result),
    AW = maps:get(away_wins, Result),
    Dr = maps:get(draws, Result),
    ?assertEqual(TM, HW + AW + Dr).

get_competition_matches_test() ->
    setup(),
    Result = bsm_query:get_competition_matches(#{
        <<"competition">> => <<"libertadores">>,
        <<"season">> => 2018,
        <<"limit">> => 30
    }),
    Total = maps:get(total, Result),
    ?assert(Total > 0).

%% ===================================================================
%% MCP Protocol Tests
%% ===================================================================
mcp_tool_definitions_test_() ->
    {timeout, 30, fun() ->
        setup(),
        Tools = bsm_mcp_server:tool_definitions_test(),
        ?assert(length(Tools) >= 8)
    end}.

mcp_search_matches_tool_test() ->
    setup(),
    Result = bsm_mcp_server:call_tool_test(<<"search_matches">>,
        #{<<"team">> => <<"Palmeiras">>, <<"season">> => 2022, <<"limit">> => 10}),
    ?assertMatch(#{<<"content">> := [#{<<"type">> := <<"text">>}]}, Result),
    [#{<<"text">> := Text}] = maps:get(<<"content">>, Result),
    ?assertNotEqual(nomatch, binary:match(Text, <<"Found">>)).

mcp_get_standings_tool_test() ->
    setup(),
    Result = bsm_mcp_server:call_tool_test(<<"get_standings">>,
        #{<<"season">> => 2019, <<"competition">> => <<"brasileirao">>}),
    [#{<<"text">> := Text}] = maps:get(<<"content">>, Result),
    ?assertNotEqual(nomatch, binary:match(Text, <<"Standings">>)).

mcp_search_players_tool_test_() ->
    {timeout, 30, fun() ->
        setup(),
        Result = bsm_mcp_server:call_tool_test(<<"search_players">>,
            #{<<"nationality">> => <<"Brazil">>, <<"min_rating">> => 80, <<"max_results">> => 10}),
        [#{<<"text">> := Text}] = maps:get(<<"content">>, Result),
        ?assertNotEqual(nomatch, binary:match(Text, <<"Found">>))
    end}.

mcp_head_to_head_tool_test() ->
    setup(),
    Result = bsm_mcp_server:call_tool_test(<<"head_to_head">>,
        #{<<"team1">> => <<"Corinthians">>, <<"team2">> => <<"Palmeiras">>}),
    [#{<<"text">> := Text}] = maps:get(<<"content">>, Result),
    ?assertNotEqual(nomatch, binary:match(Text, <<"Head-to-head">>)).

mcp_json_rpc_initialize_test() ->
    Msg = #{
        <<"jsonrpc">> => <<"2.0">>,
        <<"id">> => 1,
        <<"method">> => <<"initialize">>,
        <<"params">> => #{<<"protocolVersion">> => <<"2024-11-05">>}
    },
    Result = bsm_mcp_server:handle_message_test(Msg),
    ?assertMatch(#{<<"result">> := #{<<"protocolVersion">> := _}}, Result).

mcp_json_rpc_tools_list_test() ->
    Msg = #{
        <<"jsonrpc">> => <<"2.0">>,
        <<"id">> => 2,
        <<"method">> => <<"tools/list">>,
        <<"params">> => #{}
    },
    Result = bsm_mcp_server:handle_message_test(Msg),
    ?assertMatch(#{<<"result">> := #{<<"tools">> := _}}, Result),
    #{<<"result">> := #{<<"tools">> := Tools}} = Result,
    ?assert(length(Tools) >= 8).

mcp_cross_file_query_test_() ->
    {timeout, 30, fun() ->
        %% Test that player and match data can be used together
        setup(),
        %% Get players from a club present in the FIFA dataset
        PlayerResult = bsm_query:search_players(#{
            <<"club">> => <<"Santos">>,
            <<"max_results">> => 5
        }),
        ?assert(maps:get(total, PlayerResult) > 0),
        %% Get matches for Flamengo
        MatchResult = bsm_query:search_matches(#{
            <<"team">> => <<"Flamengo">>,
            <<"limit">> => 10
        }),
        ?assert(maps:get(total, MatchResult) > 0)
    end}.
