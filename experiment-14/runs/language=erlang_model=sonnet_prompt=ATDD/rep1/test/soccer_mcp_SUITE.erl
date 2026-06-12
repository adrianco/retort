%% Acceptance tests for the Brazilian Soccer MCP Server.
%% Tests exercise the system only through the MCP JSON-RPC protocol interface.
%% Each test is independent and uses data loaded once per suite (read-only data).

-module(soccer_mcp_SUITE).
-include_lib("common_test/include/ct.hrl").
-compile(export_all).

all() ->
    [
        ac01_initialize_returns_capabilities,
        ac02_tools_list_returns_expected_tools,
        ac03_find_matches_by_team,
        ac04_find_matches_by_competition_and_season,
        ac05_find_matches_normalizes_team_names,
        ac06_get_team_stats_returns_record,
        ac07_find_players_by_name,
        ac08_find_players_by_nationality,
        ac09_find_players_by_club,
        ac10_get_head_to_head_returns_record,
        ac11_get_standings_shows_champion,
        ac12_get_statistics_biggest_wins,
        ac13_get_statistics_avg_goals,
        ac14_find_copa_do_brasil_matches,
        ac15_find_libertadores_matches
    ].

init_per_suite(Config) ->
    {ok, CWD} = file:get_cwd(),
    ct:log("CWD: ~s", [CWD]),
    %% Find project root (where rebar.config lives) to build absolute data path.
    ProjectRoot = find_project_root(CWD),
    ct:log("Project root: ~s", [ProjectRoot]),
    DataDir = filename:join([ProjectRoot, "data", "kaggle"]),
    ct:log("Data dir: ~s (exists: ~p)", [DataDir, filelib:is_dir(DataDir)]),
    %% Force absolute data path via env var so soccer_data finds the CSVs.
    os:putenv("DATA_DIR", DataDir),
    %% Reset in case a previous run cached an empty dataset.
    soccer_data:reset(),
    ok = soccer_data:init(),
    SampleMatches = soccer_data:find_matches_all(#{competition => <<"brasileirao">>}),
    ct:log("Brasileirao matches loaded: ~p", [length(SampleMatches)]),
    Config.

find_project_root(Dir) ->
    case filelib:is_file(filename:join(Dir, "rebar.config")) of
        true  -> Dir;
        false ->
            Parent = filename:dirname(Dir),
            case Parent =:= Dir of
                true  -> error(no_project_root_found);
                false -> find_project_root(Parent)
            end
    end.

end_per_suite(_Config) ->
    ok.

init_per_testcase(_TestCase, Config) ->
    Config.

end_per_testcase(_TestCase, _Config) ->
    ok.

%%--------------------------------------------------------------------
%% AC-01: Initialize returns MCP capabilities
%%--------------------------------------------------------------------
ac01_initialize_returns_capabilities(_Config) ->
    Resp = send_request(<<"initialize">>, #{
        <<"protocolVersion">> => <<"2024-11-05">>,
        <<"capabilities">> => #{},
        <<"clientInfo">> => #{<<"name">> => <<"test">>, <<"version">> => <<"1.0">>}
    }),
    #{<<"result">> := Result} = Resp,
    #{<<"protocolVersion">> := _} = Result,
    #{<<"capabilities">> := Caps} = Result,
    #{<<"tools">> := _} = Caps,
    #{<<"serverInfo">> := #{<<"name">> := Name}} = Result,
    true = is_binary(Name),
    ok.

%%--------------------------------------------------------------------
%% AC-02: Tools list returns at least the 6 required tools
%%--------------------------------------------------------------------
ac02_tools_list_returns_expected_tools(_Config) ->
    Resp = send_request(<<"tools/list">>, #{}),
    #{<<"result">> := #{<<"tools">> := Tools}} = Resp,
    ToolNames = [maps:get(<<"name">>, T) || T <- Tools],
    ExpectedTools = [
        <<"find_matches">>,
        <<"get_team_stats">>,
        <<"find_players">>,
        <<"get_head_to_head">>,
        <<"get_standings">>,
        <<"get_statistics">>
    ],
    lists:foreach(fun(Expected) ->
        true = lists:member(Expected, ToolNames),
        ct:log("Tool found: ~s", [Expected])
    end, ExpectedTools),
    true = length(Tools) >= 6,
    ok.

%%--------------------------------------------------------------------
%% AC-03: Find matches by team name
%%--------------------------------------------------------------------
ac03_find_matches_by_team(_Config) ->
    Result = call_tool(<<"find_matches">>, #{<<"team">> => <<"Flamengo">>}),
    #{<<"total_found">> := TotalFound, <<"matches">> := Matches} = Result,
    ct:log("Flamengo matches found: ~p (showing ~p)", [TotalFound, length(Matches)]),
    true = TotalFound > 0,
    true = length(Matches) > 0,
    %% Every returned match should involve Flamengo
    lists:foreach(fun(Match) ->
        Home = maps:get(<<"home_team">>, Match),
        Away = maps:get(<<"away_team">>, Match),
        InvolvedFlamengo = contains(Home, <<"Flamengo">>) orelse contains(Away, <<"Flamengo">>),
        true = InvolvedFlamengo
    end, Matches),
    ok.

%%--------------------------------------------------------------------
%% AC-04: Find matches filtered by competition and season
%%--------------------------------------------------------------------
ac04_find_matches_by_competition_and_season(_Config) ->
    Result = call_tool(<<"find_matches">>, #{
        <<"competition">> => <<"brasileirao">>,
        <<"season">> => 2019
    }),
    #{<<"total_found">> := TotalFound, <<"matches">> := Matches} = Result,
    ct:log("Brasileirao 2019 matches: ~p", [TotalFound]),
    %% 2019 Brasileirao had 380 matches
    true = TotalFound >= 380,
    %% All returned matches should be from 2019 Brasileirao
    lists:foreach(fun(Match) ->
        2019 = maps:get(<<"season">>, Match),
        <<"brasileirao">> = maps:get(<<"competition">>, Match)
    end, Matches),
    ok.

%%--------------------------------------------------------------------
%% AC-05: Team name normalization - "Flamengo" and "Flamengo-RJ" give same results
%%--------------------------------------------------------------------
ac05_find_matches_normalizes_team_names(_Config) ->
    R1 = call_tool(<<"find_matches">>, #{<<"team">> => <<"Flamengo">>}),
    R2 = call_tool(<<"find_matches">>, #{<<"team">> => <<"Flamengo-RJ">>}),
    #{<<"total_found">> := N1} = R1,
    #{<<"total_found">> := N2} = R2,
    ct:log("Flamengo: ~p, Flamengo-RJ: ~p", [N1, N2]),
    %% Both should return the same number of matches
    true = N1 =:= N2,
    true = N1 > 0,
    ok.

%%--------------------------------------------------------------------
%% AC-06: Team statistics include win/draw/loss record
%%--------------------------------------------------------------------
ac06_get_team_stats_returns_record(_Config) ->
    Result = call_tool(<<"get_team_stats">>, #{
        <<"team">> => <<"Palmeiras">>,
        <<"competition">> => <<"brasileirao">>,
        <<"season">> => 2022
    }),
    ct:log("Palmeiras 2022 stats: ~p", [Result]),
    #{<<"team">> := Team, <<"matches_played">> := Played,
      <<"wins">> := Wins, <<"draws">> := Draws, <<"losses">> := Losses,
      <<"goals_for">> := GF, <<"goals_against">> := GA} = Result,
    true = contains(Team, <<"Palmeiras">>),
    true = Played > 0,
    true = Wins + Draws + Losses =:= Played,
    true = GF >= 0,
    true = GA >= 0,
    ok.

%%--------------------------------------------------------------------
%% AC-07: Find players by name
%%--------------------------------------------------------------------
ac07_find_players_by_name(_Config) ->
    Result = call_tool(<<"find_players">>, #{<<"name">> => <<"Neymar">>}),
    #{<<"total_found">> := TotalFound, <<"players">> := Players} = Result,
    ct:log("Neymar search: ~p results", [TotalFound]),
    true = TotalFound > 0,
    true = length(Players) > 0,
    %% At least one result should be Neymar Jr
    [First | _] = Players,
    #{<<"name">> := PlayerName} = First,
    true = contains(PlayerName, <<"Neymar">>),
    ok.

%%--------------------------------------------------------------------
%% AC-08: Find Brazilian players by nationality
%%--------------------------------------------------------------------
ac08_find_players_by_nationality(_Config) ->
    Result = call_tool(<<"find_players">>, #{
        <<"nationality">> => <<"Brazil">>,
        <<"limit">> => 10
    }),
    #{<<"total_found">> := TotalFound, <<"players">> := Players} = Result,
    ct:log("Brazilian players found: ~p", [TotalFound]),
    true = TotalFound > 500,
    %% All returned players should be Brazilian
    lists:foreach(fun(Player) ->
        Nat = maps:get(<<"nationality">>, Player),
        true = contains(Nat, <<"Brazil">>)
    end, Players),
    %% Players should be sorted by overall rating descending
    Ratings = [maps:get(<<"overall">>, P) || P <- Players],
    true = is_sorted_descending(Ratings),
    ok.

%%--------------------------------------------------------------------
%% AC-09: Find players by club (using Santos - no accented characters)
%%--------------------------------------------------------------------
ac09_find_players_by_club(_Config) ->
    Result = call_tool(<<"find_players">>, #{
        <<"club">> => <<"Santos">>,
        <<"limit">> => 30
    }),
    #{<<"total_found">> := TotalFound, <<"players">> := Players} = Result,
    ct:log("Santos players found: ~p", [TotalFound]),
    true = TotalFound > 0,
    lists:foreach(fun(Player) ->
        Club = maps:get(<<"club">>, Player),
        true = contains(Club, <<"Santos">>)
    end, Players),
    ok.

%%--------------------------------------------------------------------
%% AC-10: Head-to-head record between two teams
%%--------------------------------------------------------------------
ac10_get_head_to_head_returns_record(_Config) ->
    Result = call_tool(<<"get_head_to_head">>, #{
        <<"team1">> => <<"Flamengo">>,
        <<"team2">> => <<"Fluminense">>
    }),
    ct:log("Flamengo vs Fluminense H2H: ~p", [Result]),
    #{<<"team1">> := T1, <<"team2">> := T2,
      <<"total_matches">> := Total,
      <<"team1_wins">> := W1, <<"team2_wins">> := W2, <<"draws">> := D} = Result,
    true = contains(T1, <<"Flamengo">>),
    true = contains(T2, <<"Fluminense">>),
    true = Total > 0,
    true = W1 + W2 + D =:= Total,
    ok.

%%--------------------------------------------------------------------
%% AC-11: Standings for 2019 Brasileirao shows Flamengo as champion
%%--------------------------------------------------------------------
ac11_get_standings_shows_champion(_Config) ->
    Result = call_tool(<<"get_standings">>, #{
        <<"competition">> => <<"brasileirao">>,
        <<"season">> => 2019
    }),
    #{<<"standings">> := Standings, <<"season">> := Season} = Result,
    2019 = Season,
    true = length(Standings) > 0,
    [Champion | _] = Standings,
    #{<<"position">> := 1, <<"team">> := ChampTeam, <<"points">> := Pts} = Champion,
    ct:log("2019 Champion: ~s with ~p points", [ChampTeam, Pts]),
    true = contains(ChampTeam, <<"Flamengo">>),
    %% Flamengo won with 90 points in 2019
    true = Pts >= 88,
    ok.

%%--------------------------------------------------------------------
%% AC-12: Statistical analysis - biggest wins
%%--------------------------------------------------------------------
ac12_get_statistics_biggest_wins(_Config) ->
    Result = call_tool(<<"get_statistics">>, #{
        <<"stat_type">> => <<"biggest_wins">>,
        <<"limit">> => 10
    }),
    #{<<"stat_type">> := StatType, <<"results">> := Results} = Result,
    <<"biggest_wins">> = StatType,
    true = length(Results) > 0,
    [Biggest | _] = Results,
    #{<<"home_goal">> := HG, <<"away_goal">> := AG} = Biggest,
    GD = abs(HG - AG),
    ct:log("Biggest win: ~p-~p (diff: ~p)", [HG, AG, GD]),
    true = GD >= 5,
    ok.

%%--------------------------------------------------------------------
%% AC-13: Statistical analysis - average goals per match
%%--------------------------------------------------------------------
ac13_get_statistics_avg_goals(_Config) ->
    Result = call_tool(<<"get_statistics">>, #{
        <<"stat_type">> => <<"avg_goals">>
    }),
    #{<<"stat_type">> := StatType, <<"total_matches">> := TotalMatches,
      <<"avg_goals_per_match">> := AvgGoals} = Result,
    <<"avg_goals">> = StatType,
    true = TotalMatches > 1000,
    true = AvgGoals > 1.0,
    true = AvgGoals < 5.0,
    ct:log("Avg goals per match: ~p (from ~p matches)", [AvgGoals, TotalMatches]),
    ok.

%%--------------------------------------------------------------------
%% AC-14: Find Copa do Brasil matches
%%--------------------------------------------------------------------
ac14_find_copa_do_brasil_matches(_Config) ->
    Result = call_tool(<<"find_matches">>, #{
        <<"competition">> => <<"copa_do_brasil">>,
        <<"limit">> => 20
    }),
    #{<<"total_found">> := TotalFound, <<"matches">> := Matches} = Result,
    ct:log("Copa do Brasil matches: ~p", [TotalFound]),
    true = TotalFound > 100,
    lists:foreach(fun(Match) ->
        <<"copa_do_brasil">> = maps:get(<<"competition">>, Match)
    end, Matches),
    ok.

%%--------------------------------------------------------------------
%% AC-15: Find Copa Libertadores matches
%%--------------------------------------------------------------------
ac15_find_libertadores_matches(_Config) ->
    Result = call_tool(<<"find_matches">>, #{
        <<"competition">> => <<"libertadores">>,
        <<"limit">> => 20
    }),
    #{<<"total_found">> := TotalFound, <<"matches">> := Matches} = Result,
    ct:log("Libertadores matches: ~p", [TotalFound]),
    true = TotalFound > 100,
    lists:foreach(fun(Match) ->
        <<"libertadores">> = maps:get(<<"competition">>, Match)
    end, Matches),
    ok.

%%--------------------------------------------------------------------
%% Test Helpers
%%--------------------------------------------------------------------

%% Send an MCP request and return the full JSON-RPC response as Erlang term.
send_request(Method, Params) ->
    Req = #{
        <<"jsonrpc">> => <<"2.0">>,
        <<"id">> => 1,
        <<"method">> => Method,
        <<"params">> => Params
    },
    ReqBin = iolist_to_binary(json:encode(Req)),
    soccer_mcp:handle_message(ReqBin).

%% Call an MCP tool and return the parsed JSON result from the text content.
call_tool(ToolName, Args) ->
    Resp = send_request(<<"tools/call">>, #{
        <<"name">> => ToolName,
        <<"arguments">> => Args
    }),
    #{<<"result">> := #{<<"content">> := [#{<<"text">> := TextBin}]}} = Resp,
    json:decode(TextBin).

%% Case-insensitive substring containment check.
contains(Subject, Pattern) when is_binary(Subject), is_binary(Pattern) ->
    string:find(string:lowercase(Subject), string:lowercase(Pattern)) =/= nomatch.

%% Check that a list is sorted in descending order.
is_sorted_descending([]) -> true;
is_sorted_descending([_]) -> true;
is_sorted_descending([H1, H2 | T]) ->
    H1 >= H2 andalso is_sorted_descending([H2 | T]).
