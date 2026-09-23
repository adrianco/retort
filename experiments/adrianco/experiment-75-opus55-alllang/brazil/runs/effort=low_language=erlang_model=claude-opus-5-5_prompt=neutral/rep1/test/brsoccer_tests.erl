%% BDD-style scenarios (Given/When/Then) for the Brazilian Soccer MCP server.
-module(brsoccer_tests).
-include_lib("eunit/include/eunit.hrl").

-define(Q, brsoccer_query).

%% ------------------------------------------------------------ unit: parsing & normalization

csv_quoted_fields_test() ->
    Rows = brsoccer_csv:parse(<<16#EF, 16#BB, 16#BF, "a,b,c\r\n\"x, y\",\"he said \"\"hi\"\"\",3\n">>),
    ?assertEqual([#{<<"a">> => <<"x, y">>, <<"b">> => <<"he said \"hi\"">>, <<"c">> => <<"3">>}], Rows).

team_name_variations_test_() ->
    K = fun brsoccer_norm:team_key/1,
    [?_assertEqual(K(<<"Palmeiras-SP">>), K(<<"Palmeiras">>)),
     ?_assertEqual(K(<<"São Paulo"/utf8>>), K(<<"Sao Paulo-SP">>)),
     ?_assertEqual(K(<<"Grêmio"/utf8>>), K(<<"Gremio">>)),
     ?_assertEqual(K(<<"Sport Club Corinthians Paulista">>), K(<<"Corinthians">>)),
     ?_assertEqual(K(<<"Atletico Mineiro">>), K(<<"Atlético-MG"/utf8>>)),
     ?_assertEqual(K(<<"Athletico Paranaense">>), K(<<"Athletico-PR">>)),
     ?_assertNotEqual(K(<<"Atletico-MG">>), K(<<"Atletico-PR">>)),
     ?_assertEqual(K(<<"Vasco Da Gama RJ">>), K(<<"Vasco">>)),
     ?_assertEqual(K(<<"America - MG">>), K(<<"America MG">>)),
     ?_assert(brsoccer_norm:team_matches(<<"Flamengo">>, <<"Flamengo-RJ">>)),
     ?_assertNot(brsoccer_norm:team_matches(<<"Flamengo">>, <<"Fluminense-RJ">>))].

date_formats_test_() ->
    D = fun brsoccer_norm:date/1,
    [?_assertEqual(<<"2003-03-29">>, D(<<"29/03/2003">>)),
     ?_assertEqual(<<"2012-05-19">>, D(<<"2012-05-19 18:30:00">>)),
     ?_assertEqual(<<"2023-09-24">>, D(<<"2023-09-24">>))].

%% ------------------------------------------------------------ scenarios over real data

data_test_() ->
    {setup, fun() -> ok = brsoccer_data:load() end,
     {timeout, 120,
      [{"all 6 CSV files are loaded", fun all_files_loaded/0},
       {"matches between Flamengo and Fluminense", fun fla_flu/0},
       {"Palmeiras 2023 statistics", fun palmeiras_2023/0},
       {"Corinthians home record 2022", fun corinthians_home_2022/0},
       {"2019 Brasileirão champion", fun champion_2019/0},
       {"historical seasons from Brazilian-format dates", fun champion_2008/0},
       {"relegated teams 2020", fun relegated_2020/0},
       {"top scorer team in a season", fun top_scoring/0},
       {"head to head Palmeiras vs Santos", fun h2h/0},
       {"last Flamengo vs Corinthians match", fun last_match/0},
       {"Copa do Brasil finals", fun cup_finals/0},
       {"Libertadores 2018 knockout stage", fun libertadores/0},
       {"average goals and home win rate", fun league_summary/0},
       {"best away record", fun best_away/0},
       {"biggest wins", fun biggest_wins/0},
       {"derbies in 2023", fun derbies/0},
       {"competitions played by Palmeiras", fun competitions/0},
       {"date range filter", fun date_range/0},
       {"extended stats in BR-Football data", fun extended_stats/0},
       {"Brazilian players", fun brazilian_players/0},
       {"player by name", fun player_by_name/0},
       {"players at a Brazilian club", fun club_players/0},
       {"forwards filter", fun forwards/0},
       {"Brazilian players at Brazilian clubs", fun br_clubs/0},
       {"cross-file: club players plus club matches", fun cross_file/0},
       {"MCP protocol", fun mcp_protocol/0},
       {"MCP tools each return text", fun mcp_all_tools/0},
       {"query performance", fun performance/0}]}}.

all_files_loaded() ->
    C = maps:from_list(brsoccer_data:source_counts()),
    ?assertEqual(18207, maps:get(fifa, C)),
    ?assertEqual(6886, maps:get(historical, C)),
    ?assertEqual(10296, maps:get(br_football, C)),
    ?assert(maps:get(brasileirao, C) > 4000),
    ?assert(maps:get(copa_do_brasil, C) > 1300),
    ?assert(maps:get(libertadores, C) > 1200).

%% Scenario: Find matches between two teams
fla_flu() ->
    %% When I search for matches between "Flamengo" and "Fluminense"
    Ms = ?Q:matches(#{team => <<"Flamengo">>, opponent => <<"Fluminense">>}),
    %% Then I should receive a list of matches, each with date, scores and competition
    ?assert(length(Ms) > 20),
    lists:foreach(fun(M = #{home := H, away := A}) ->
                          ?assert(is_integer(maps:get(hg, M))),
                          ?assert(is_integer(maps:get(ag, M))),
                          ?assertMatch(<<_:4/binary, "-", _:2/binary, "-", _:2/binary>>, maps:get(date, M)),
                          ?assert(byte_size(maps:get(competition, M)) > 0),
                          ?assertEqual(lists:sort([<<"flamengo">>, <<"fluminense">>]),
                                       lists:sort([brsoccer_norm:team_key(H), brsoccer_norm:team_key(A)]))
                  end, Ms),
    {ok, Text} = brsoccer_tools:call(<<"head_to_head">>, #{<<"team_a">> => <<"Flamengo">>,
                                                          <<"team_b">> => <<"Fluminense">>}),
    ?assertMatch({_, _}, binary:match(Text, <<"Head-to-head in dataset: Flamengo">>)).

%% Scenario: Get team statistics
palmeiras_2023() ->
    R = ?Q:team_record(<<"Palmeiras">>, #{season => 2023}),
    #{matches := N, wins := W, draws := D, losses := L, goals_for := GF, goals_against := GA} = R,
    ?assert(N > 38),
    ?assertEqual(N, W + D + L),
    ?assert(GF > 0 andalso GA > 0).

corinthians_home_2022() ->
    R = ?Q:team_record(<<"Corinthians">>, #{season => 2022, venue => <<"home">>,
                                             competition => <<"Brasileirão"/utf8>>}),
    ?assertEqual(19, maps:get(matches, R)).

champion_2019() ->
    [First, Second | _] = T = ?Q:standings(2019),
    ?assertEqual(20, length(T)),
    ?assertMatch(#{team := <<"Flamengo">>, points := 90, wins := 28, draws := 6, losses := 4}, First),
    ?assertMatch(#{team := <<"Santos">>, points := 74}, Second).

champion_2008() ->
    [#{team := T} | _] = ?Q:standings(2008),
    ?assertEqual(<<"São Paulo"/utf8>>, T),
    [#{team := T9} | _] = ?Q:standings(2009),
    ?assertEqual(<<"Flamengo">>, T9).

relegated_2020() ->
    Keys = [brsoccer_norm:team_key(T) || #{team := T} <- ?Q:relegated(2020)],
    ?assertEqual(lists:sort([<<"vasco">>, <<"goias">>, <<"coritiba">>, <<"botafogo">>]), lists:sort(Keys)).

top_scoring() ->
    [#{team := T} | _] = ?Q:goals_ranking(#{season => 2019, competition => <<"Brasileirão"/utf8>>}),
    ?assertEqual(<<"Flamengo">>, T).

h2h() ->
    H = ?Q:head_to_head(<<"Palmeiras">>, <<"Santos">>, #{}),
    N = length(maps:get(matches, H)),
    ?assert(N > 20),
    ?assertEqual(N, maps:get(a_wins, H) + maps:get(b_wins, H) + maps:get(draws, H)).

last_match() ->
    M = ?Q:last_match(<<"Flamengo">>, <<"Corinthians">>),
    Dates = [D || #{date := D} <- ?Q:matches(#{team => <<"Flamengo">>, opponent => <<"Corinthians">>})],
    ?assertEqual(lists:max(Dates), maps:get(date, M)).

cup_finals() ->
    Fs = ?Q:matches(#{competition => <<"Copa do Brasil">>, stage => <<"final">>}),
    ?assert(length(Fs) >= 10),
    ?assert(lists:any(fun(#{season := S, home := H}) -> S =:= 2020 andalso H =:= <<"Palmeiras">> end, Fs)).

libertadores() ->
    Ms = ?Q:matches(#{competition => <<"Libertadores">>, season => 2018}),
    Stages = lists:usort([S || #{stage := S} <- Ms]),
    ?assert(lists:member(<<"final">>, Stages)),
    ?assert(lists:member(<<"semifinals">>, Stages)).

league_summary() ->
    #{avg_goals := A, home_win_rate := H, matches := N} =
        ?Q:league_summary(#{competition => <<"Brasileirão"/utf8>>}),
    ?assert(N > 8000),
    ?assert(A > 2.0 andalso A < 3.0),
    ?assert(H > 40.0 andalso H < 60.0).

best_away() ->
    [#{win_rate := W1} , #{win_rate := W2} | _] = ?Q:best_records(<<"away">>, #{competition => <<"Brasileirão"/utf8>>}, 50),
    ?assert(W1 >= W2).

biggest_wins() ->
    [#{hg := H, ag := A} | Rest] = ?Q:biggest_wins(#{}, 10),
    Top = abs(H - A),
    ?assert(Top >= 7),
    ?assert(lists:all(fun(#{hg := X, ag := Y}) -> abs(X - Y) =< Top end, Rest)).

derbies() ->
    Ds = ?Q:derbies(#{season => 2023}),
    Names = lists:usort([N || {N, _} <- Ds]),
    ?assert(lists:member(<<"Fla-Flu">>, Names)),
    ?assert(lists:member(<<"Grenal">>, Names)).

competitions() ->
    Cs = [C || {C, _, _} <- ?Q:team_competitions(<<"Palmeiras">>)],
    ?assert(lists:member(<<"Brasileirão"/utf8>>, Cs)),
    ?assert(lists:member(<<"Copa do Brasil">>, Cs)),
    ?assert(lists:member(<<"Libertadores">>, Cs)).

date_range() ->
    Ms = ?Q:matches(#{team => <<"Santos">>, date_from => <<"01/01/2015">>, date_to => <<"2015-12-31">>}),
    ?assert(length(Ms) > 30),
    ?assert(lists:all(fun(#{date := <<"2015", _/binary>>}) -> true; (_) -> false end, Ms)).

extended_stats() ->
    Ms = [M || M = #{source := br_football} <- ?Q:matches(#{team => <<"Gremio">>, season => 2023})],
    ?assert(length(Ms) > 0),
    ?assert(lists:any(fun(#{stats := #{home_corner := C}}) -> is_integer(C) end, Ms)).

brazilian_players() ->
    Ps = ?Q:players(#{nationality => <<"Brazil">>}),
    ?assertEqual(827, length(Ps)),
    ?assertMatch([#{name := <<"Neymar Jr">>, overall := 92} | _], Ps).

player_by_name() ->
    ?assertMatch([#{name := <<"Neymar Jr">>, club := <<"Paris Saint-Germain">>}], ?Q:players(#{name => <<"neymar">>})),
    %% "Who is Gabriel Barbosa?" - not in FIFA 19 under that name; partial matches are offered.
    ?assertEqual([], ?Q:players(#{name => <<"gabriel barbosa">>})),
    {ok, T} = brsoccer_tools:call(<<"search_players">>, #{<<"name">> => <<"Gabriel Barbosa">>}),
    ?assertMatch({_, _}, binary:match(T, <<"closest partial matches">>)),
    ?assertMatch({_, _}, binary:match(T, <<"Gabriel">>)).

club_players() ->
    Ps = ?Q:players(#{club => <<"Gremio">>}),
    ?assertEqual(20, length(Ps)),
    ?assert(lists:all(fun(#{club := C}) -> C =:= <<"Grêmio"/utf8>> end, Ps)).

forwards() ->
    Ps = ?Q:players(#{club => <<"Santos">>, position => <<"forwards">>}),
    ?assert(length(Ps) > 0),
    ?assert(lists:all(fun(#{position := P}) -> lists:member(P, [<<"ST">>, <<"CF">>, <<"LW">>, <<"RW">>, <<"LF">>, <<"RF">>, <<"LS">>, <<"RS">>]) end, Ps)).

br_clubs() ->
    Cs = ?Q:brazilian_club_players(),
    Names = [C || {C, _, _} <- Cs],
    ?assert(lists:member(<<"Grêmio"/utf8>>, Names)),
    ?assertNot(lists:member(<<"Boavista FC">>, Names)),
    ?assert(length(Cs) >= 15).

cross_file() ->
    %% FIFA club "Atlético Mineiro" resolves to the same team as "Atletico-MG" in match data.
    [#{club := Club} | _] = ?Q:players(#{club => <<"Atletico Mineiro">>}),
    Ms = ?Q:matches(#{team => Club}),
    ?assert(length(Ms) > 100),
    ?assert(lists:all(fun(M) -> ?Q:is_team(Club, M) =/= false end, Ms)).

mcp_protocol() ->
    Init = brsoccer:handle(#{<<"jsonrpc">> => <<"2.0">>, <<"id">> => 1, <<"method">> => <<"initialize">>}),
    ?assertMatch(#{id := 1, result := #{serverInfo := _, capabilities := #{tools := _}}}, Init),
    ?assertEqual(noreply, brsoccer:handle(#{<<"method">> => <<"notifications/initialized">>})),
    #{result := #{tools := Tools}} = brsoccer:handle(#{<<"id">> => 2, <<"method">> => <<"tools/list">>}),
    ?assert(length(Tools) >= 10),
    Req = json:decode(<<"{\"jsonrpc\":\"2.0\",\"id\":3,\"method\":\"tools/call\",\"params\":"
                        "{\"name\":\"standings\",\"arguments\":{\"season\":2019}}}">>),
    #{result := #{content := [#{text := T}], isError := false}} = Resp = brsoccer:handle(Req),
    ?assertMatch({_, _}, binary:match(T, <<"1. Flamengo - 90 pts (28W, 6D, 4L">>)),
    %% response must be encodable JSON
    _ = iolist_to_binary(json:encode(Resp)),
    ?assertMatch(#{error := #{code := -32601}}, brsoccer:handle(#{<<"id">> => 4, <<"method">> => <<"nope">>})),
    #{result := #{isError := true}} =
        brsoccer:handle(#{<<"id">> => 5, <<"method">> => <<"tools/call">>,
                          <<"params">> => #{<<"name">> => <<"team_stats">>, <<"arguments">> => #{}}}).

%% 20+ sample questions answered through the MCP tool layer.
mcp_all_tools() ->
    Calls = [{<<"search_matches">>, #{<<"team">> => <<"Palmeiras">>, <<"season">> => 2023}},
             {<<"search_matches">>, #{<<"home_team">> => <<"Flamengo">>, <<"away_team">> => <<"Fluminense">>}},
             {<<"search_matches">>, #{<<"competition">> => <<"Copa do Brasil">>, <<"stage">> => <<"final">>}},
             {<<"head_to_head">>, #{<<"team_a">> => <<"Palmeiras">>, <<"team_b">> => <<"Santos">>}},
             {<<"head_to_head">>, #{<<"team_a">> => <<"Grêmio"/utf8>>, <<"team_b">> => <<"Internacional">>}},
             {<<"team_stats">>, #{<<"team">> => <<"Corinthians">>, <<"season">> => 2022, <<"venue">> => <<"home">>}},
             {<<"team_stats">>, #{<<"team">> => <<"São Paulo"/utf8>>}},
             {<<"standings">>, #{<<"season">> => 2019}},
             {<<"standings">>, #{<<"season">> => 2020}},
             {<<"league_stats">>, #{<<"competition">> => <<"Brasileirão"/utf8>>}},
             {<<"league_stats">>, #{<<"season">> => 2018}},
             {<<"league_stats">>, #{<<"season">> => 2019}},
             {<<"biggest_wins">>, #{}},
             {<<"best_records">>, #{<<"venue">> => <<"home">>}},
             {<<"best_records">>, #{<<"venue">> => <<"away">>}},
             {<<"top_scoring_teams">>, #{<<"season">> => 2023, <<"competition">> => <<"Serie A">>}},
             {<<"derbies">>, #{<<"season">> => 2023}},
             {<<"team_competitions">>, #{<<"team">> => <<"Palmeiras">>}},
             {<<"search_players">>, #{<<"nationality">> => <<"Brazil">>}},
             {<<"search_players">>, #{<<"name">> => <<"Gabriel Barbosa">>}},
             {<<"search_players">>, #{<<"club">> => <<"Cruzeiro">>}},
             {<<"brazilian_clubs_players">>, #{}},
             {<<"dataset_info">>, #{}}],
    lists:foreach(fun({N, A}) ->
                          {ok, T} = brsoccer_tools:call(N, A),
                          ?assertNotMatch({N, A, <<"Found 0", _/binary>>}, {N, A, T}),
                          ?assert(byte_size(T) > 20)
                  end, Calls),
    ?assert(length(Calls) >= 20).

performance() ->
    {T1, _} = timer:tc(fun() -> brsoccer_tools:call(<<"search_players">>, #{<<"name">> => <<"Neymar">>}) end),
    {T2, _} = timer:tc(fun() -> brsoccer_tools:call(<<"best_records">>, #{<<"venue">> => <<"away">>}) end),
    {T3, _} = timer:tc(fun() -> brsoccer_tools:call(<<"standings">>, #{<<"season">> => 2015}) end),
    ?assert(T1 < 2000000),
    ?assert(T2 < 5000000),
    ?assert(T3 < 5000000).
