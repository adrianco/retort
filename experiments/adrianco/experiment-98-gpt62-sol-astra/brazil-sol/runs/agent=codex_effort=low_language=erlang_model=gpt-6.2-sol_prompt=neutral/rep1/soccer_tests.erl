-module(soccer_tests).
-include_lib("eunit/include/eunit.hrl").

-define(MATCH, <<"find_matches">>).
-define(TEAM, <<"team_stats">>).
-define(PLAYERS, <<"find_players">>).
-define(TABLE, <<"standings">>).
-define(ANALYZE, <<"analyze_matches">>).
-define(A, <<"Brasileirão"/utf8>>).

dataset_test_() ->
    {setup, fun() -> soccer_data:load("data/kaggle") end, fun(_) -> ok end,
     fun scenarios/1}.

scenarios(Data) ->
    Q = fun(Tool, Args) ->
        Input = maps:from_list([{atom_to_binary(K), V} || {K, V} <- maps:to_list(Args)]),
        {ok, Answer} = soccer_query:run(Tool, Input, Data),
        Answer
    end,
    [
     {"Which matches did Flamengo play against Fluminense?", fun() ->
        R = Q(?MATCH, #{team => <<"Flamengo-RJ">>, opponent => <<"Fluminense">>, status => <<"played">>}),
        ?assert(maps:get(total, R) > 25),
        lists:foreach(fun(#{date := Date, home_goals := H, away_goals := A, competition := C,
                            home_team := Home, away_team := Away}) ->
            ?assert(is_binary(Date) andalso is_integer(H) andalso is_integer(A) andalso is_binary(C)),
            ?assertEqual([<<"flamengo">>, <<"fluminense">>], lists:sort([Home, Away]))
        end, maps:get(matches, R))
     end},
     {"When did Flamengo last play Corinthians and what was the score?", fun() ->
        #{matches := [M], next_offset := 1} = Q(?MATCH, #{team => <<"Flamengo">>,
            opponent => <<"Sport Club Corinthians Paulista">>, status => <<"played">>, limit => 1}),
        ?assertMatch(#{date := <<"2023-10-08">>, home_goals := 1, away_goals := 1}, M)
     end},
     {"Which matches did Palmeiras play in 2023?", fun() ->
        #{total := N, matches := Rows} = Q(?MATCH, #{team => <<"Palmeiras-SP">>, season => 2023}),
        ?assert(N > 37),
        ?assert(lists:all(fun(#{season := Year}) -> Year =:= 2023 end, Rows))
     end},
     {"Which teams played the 2023 Copa do Brasil finals?", fun() ->
        #{total := 2, matches := [Second, First]} =
            Q(?MATCH, #{competition => <<"Copa do Brasil">>, season => 2023, stage => <<"finals">>}),
        ?assertMatch(#{home_team := <<"sao paulo">>, home_goals := 1, away_goals := 1}, Second),
        ?assertMatch(#{home_team := <<"flamengo">>, home_goals := 0, away_goals := 1}, First)
     end},
     {"What was Corinthians' 2022 Serie A home record?", fun() ->
        R = Q(?TEAM, #{team => <<"Corinthians">>, venue => <<"home">>, season => 2022, competition => ?A}),
        ?assertMatch(#{record := #{matches := 19, wins := 12, draws := 4, losses := 3,
                                   goals_for := 24, goals_against := 11}}, R),
        ?assertEqual(0, maps:get(matches, maps:get(away, R)))
     end},
     {"How did Palmeiras perform in 2023?", fun() ->
        #{record := #{matches := N, wins := W, draws := D, losses := L, goals_for := GF,
                      goals_against := GA}, by_competition := Comps} =
            Q(?TEAM, #{team => <<"Palmeiras">>, season => 2023}),
        ?assertEqual(N, W + D + L),
        ?assert(GF > GA),
        ?assert(length(Comps) >= 2)
     end},
     {"How do Palmeiras and Santos compare head to head?", fun() ->
        #{record := R, head_to_head := #{opponent := O}} = Q(?TEAM,
            #{team => <<"Palmeiras">>, opponent => <<"Santos Futebol Clube">>}),
        ?assertEqual(maps:get(matches, R), maps:get(matches, O)),
        ?assertEqual(maps:get(wins, R), maps:get(losses, O)),
        ?assertEqual(maps:get(goals_for, R), maps:get(goals_against, O)),
        ?assert(maps:get(matches, R) > 20)
     end},
     {"Who are the highest-rated Brazilian players?", fun() ->
        #{total := N, players := [First, Second]} =
            Q(?PLAYERS, #{nationality => <<"Brasil">>, limit => 2}),
        ?assert(N > 500),
        ?assertMatch(#{name := <<"Neymar Jr">>, nationality := <<"Brazil">>, overall := 92}, First),
        ?assert(maps:get(overall, Second) =< maps:get(overall, First))
     end},
     {"What are Neymar's skill ratings?", fun() ->
        R = Q(?PLAYERS, #{name => <<"NEYMAR">>, include_attributes => true}),
        ?assertMatch(#{players := [#{attributes := #{<<"Finishing">> := <<"87">>}}]}, R)
     end},
     {"Which forwards were at Santos in the FIFA snapshot?", fun() ->
        #{total := N, players := Rows} = Q(?PLAYERS, #{club => <<"Santos FC">>, position => <<"forward">>}),
        ?assert(N > 0),
        ?assert(lists:all(fun(#{club := C}) -> C =:= <<"Santos">> end, Rows))
     end},
     {"Does the snapshot list Flamengo players or Gabriel Barbosa?", fun() ->
        ?assertMatch(#{total := 0, players := []}, Q(?PLAYERS,
            #{club => <<"Flamengo">>, club_match => <<"contains">>})),
        ?assertMatch(#{total := 0, players := []}, Q(?PLAYERS, #{name => <<"Gabriel Barbosa">>}))
     end},
     {"Who won the 2019 Brasileirão on match points?", fun() ->
        R = Q(?TABLE, #{competition => ?A, season => 2019}),
        ?assertMatch(#{complete := true, matches_played := 380, calculated_champion := <<"flamengo">>,
                       standings := [#{rank := 1, points := 90, wins := 28, draws := 6,
                                       losses := 4} | _]}, R)
     end},
     {"Which clubs finished in the 2020 relegation places?", fun() ->
        R = Q(?TABLE, #{competition => ?A, season => 2020}),
        ?assertMatch(#{complete := true, calculated_relegation_places :=
                      [<<"vasco">>, <<"goias">>, <<"coritiba">>, <<"botafogo">>]}, R)
     end},
     {"What were the results in the 2018 Libertadores knockout rounds?", fun() ->
        R = Q(?MATCH, #{competition => <<"Copa Libertadores">>, season => 2018,
                        stage => <<"knockout">>, limit => 50}),
        ?assertMatch(#{total := 30, matches := [#{details := #{stage := <<"final">>}} | _]}, R)
     end},
     {"Which team scored the most recorded goals in Série A in 2023?", fun() ->
        #{team_rankings := #{teams := [Leader]}} = Q(?ANALYZE,
            #{competition => ?A, season => 2023, rank_by => <<"goals_for">>, limit => 1}),
        ?assertMatch(#{team := <<"gremio">>, goals_for := 63}, Leader)
     end},
     {"How many goals per match did the 2019 league average?", fun() ->
        #{overall := #{matches := 380, goals := Goals, goals_per_match := Rate}} =
            Q(?ANALYZE, #{competition => ?A, season => 2019}),
        ?assertEqual(Goals / 380, Rate),
        ?assert(Rate > 2 andalso Rate < 3)
     end},
     {"How do 2018 and 2019 compare?", fun() ->
        #{by_season := [#{season := 2018, statistics := #{matches := 380}},
                        #{season := 2019, statistics := #{matches := 380}}]} =
            Q(?ANALYZE, #{competition => ?A, seasons => [2018, 2019], limit => 1})
     end},
     {"Which team had the best 2019 home record?", fun() ->
        #{team_rankings := #{teams := [Leader | _]}} = Q(?ANALYZE,
            #{competition => ?A, season => 2019, venue => <<"home">>}),
        ?assertMatch(#{team := <<"flamengo">>, matches := 19, wins := 17}, Leader)
     end},
     {"What was the biggest victory in the supplied match data?", fun() ->
        #{matches := [#{goal_margin := Margin, home_goals := H, away_goals := A}]} =
            Q(?MATCH, #{sort => <<"biggest_win">>, limit => 1}),
        ?assertEqual(abs(H-A), Margin),
        ?assert(Margin >= 8)
     end},
     {"Were there any traditional derbies in 2023?", fun() ->
        Args = #{team => <<"Flamengo">>, opponent => <<"Fluminense">>, season => 2023},
        #{total := N} = Q(?MATCH, Args#{derby => true}),
        ?assert(N >= 2),
        ?assertMatch(#{total := 0}, Q(?MATCH, Args#{derby => false}))
     end},
     {"What competitions has Palmeiras played in?", fun() ->
        #{by_competition := Comps} = Q(?TEAM, #{team => <<"Palmeiras">>}),
        Names = [C || #{competition := C} <- Comps],
        ?assert(lists:all(fun(C) -> lists:member(C, Names) end,
                         [<<"Serie A">>, <<"Copa do Brasil">>, <<"Libertadores">>]))
     end},
     {"Can I see Santos' squad alongside its match record?", fun() ->
        R = Q(<<"club_profile">>, #{team => <<"Santos">>, season => 2019, competition => ?A}),
        ?assertMatch(#{team := #{record := #{matches := 38}}, fifa_snapshot :=
                      #{players := [#{club := <<"Santos">>} | _]}}, R)
     end},
     {"What was the score in Guarani's match on 29/03/2003?", fun() ->
        R = Q(?MATCH, #{team => <<"Guarani">>, date_from => <<"29/03/2003">>,
                       date_to => <<"2003-03-29">>, venue => <<"home">>}),
        ?assertMatch(#{total := 1, matches := [#{home_goals := 4, away_goals := 2,
                      details := #{stadium := <<"Brinco de Ouro">>}}]}, R)
     end},
     {"Can I retrieve recorded corners and shots?", fun() ->
        R = Q(?MATCH, #{source => <<"BR-Football-Dataset.csv">>, competition => <<"Copa do Brasil">>,
                       date_from => <<"2023-09-24">>, date_to => <<"2023-09-24">>}),
        ?assertMatch(#{matches := [#{details := #{<<"total_corners">> := 6, <<"home_shots">> := 8}}]}, R)
     end},
     {"Are goalscorers and all six CSVs available?", fun() ->
        #{match_sources := Files, player_rows := 18207, goalscorers_available := false} =
            Q(<<"data_coverage">>, #{}),
        Counts = #{<<"Brasileirao_Matches.csv">> => 4180, <<"Brazilian_Cup_Matches.csv">> => 1337,
                   <<"Libertadores_Matches.csv">> => 1255, <<"BR-Football-Dataset.csv">> => 10296,
                   <<"novo_campeonato_brasileiro.csv">> => 6886},
        maps:foreach(fun(File, Count) ->
            ?assertMatch(#{rows := Count}, maps:get(File, Files)),
            ?assertMatch(#{total := Count, matches := [#{source := File}]}, Q(?MATCH, #{source => File, limit => 1}))
        end, Counts)
     end},
     {"Is the 2023 standings table complete?", fun() ->
        ?assertMatch(#{complete := false, matches_played := 377, expected_matches := 380,
                       calculated_champion := null}, Q(?TABLE, #{competition => ?A, season => 2023}))
     end},
     {"Are unscored games available in the schedule?", fun() ->
        #{total := N, matches := Rows} = Q(?MATCH, #{source => <<"Brasileirao_Matches.csv">>,
                                                    status => <<"scheduled">>}),
        ?assertEqual(82, N),
        ?assert(lists:all(fun(#{home_goals := H, away_goals := A}) -> H =:= null andalso A =:= null end, Rows))
     end},
     {"Can lookups and aggregates meet the response budgets?", fun() ->
        {LookupMicros, _} = timer:tc(Q, [?PLAYERS, #{nationality => <<"Brazil">>}]),
        {AggregateMicros, _} = timer:tc(Q, [?ANALYZE, #{}]),
        ?assert(LookupMicros < 2000000),
        ?assert(AggregateMicros < 5000000)
     end},
     {"Does the server give actionable input errors?", fun() ->
        ?assertMatch({error, _}, soccer_query:run(?MATCH, #{<<"date_to">> => <<"2023-02-29">>}, Data)),
        ?assertMatch({error, _}, soccer_query:run(?MATCH, #{<<"limit">> => -1}, Data)),
        ?assertMatch({error, _}, soccer_query:run(?TEAM, #{}, Data)),
        ?assertMatch({error, _}, soccer_query:run(?MATCH, #{<<"source">> => <<"unknown.csv">>}, Data))
     end}
    ].

csv_test() ->
    ?assertEqual([[<<"A">>, <<"B">>], [<<"Jul 1, 2004">>, <<"a\"b\r\nc">>], [<<"x">>, <<>>]],
                 soccer_data:csv(<<239,187,191, "A,B\r\n\"Jul 1, 2004\",\"a\"\"b\r\nc\"\r\nx,">>)).

normalization_test() ->
    ?assertEqual(<<"sao paulo">>, soccer_data:team(<<"São Paulo - SP"/utf8>>)),
    ?assertEqual(<<"atletico mineiro">>, soccer_data:team(<<"Atlético-MG"/utf8>>)),
    ?assertNotEqual(soccer_data:team(<<"América-MG"/utf8>>), soccer_data:team(<<"América-RN"/utf8>>)),
    ?assertEqual(<<"2003-03-29">>, soccer_data:date(<<"29/03/2003">>)),
    ?assertEqual(<<"2023-09-24">>, soccer_data:date(<<"2023-09-24T18:30:00">>)).

stdio_test_() -> {timeout, 15, fun stdio/0}.

stdio() ->
    Port = open_port({spawn_executable, filename:absname("_build/soccer-mcp")},
                     [binary, {line, 250000}, exit_status]),
    try
        #{<<"result">> := #{<<"protocolVersion">> := <<"2025-11-25">>}} =
            rpc(Port, 1, <<"initialize">>, #{protocolVersion => <<"2025-11-25">>}),
        send(Port, #{method => <<"notifications/initialized">>}),
        #{<<"result">> := #{<<"tools">> := Tools}} = rpc(Port, 2, <<"tools/list">>, #{}),
        ?assertEqual(lists:sort([maps:get(name, T) || T <- soccer_query:tools()]),
                     lists:sort([N || #{<<"name">> := N, <<"inputSchema">> := _} <- Tools])),
        #{<<"result">> := Result} = rpc(Port, 3, <<"tools/call">>,
            #{name => ?MATCH, arguments => #{team => <<"São Paulo"/utf8>>, venue => <<"home">>,
                                             source => <<"novo_campeonato_brasileiro.csv">>, limit => 1}}),
        #{<<"isError">> := false, <<"structuredContent">> := Structured,
          <<"content">> := [#{<<"text">> := Text}]} = Result,
        ?assertEqual(Structured, json:decode(Text)),
        ?assertMatch(#{<<"matches">> := [#{<<"home_team">> := <<"sao paulo">>,
                                           <<"original_home">> := <<"São Paulo"/utf8>>}]}, Structured),
        ?assertMatch(#{<<"result">> := #{<<"isError">> := true}},
                     rpc(Port, 4, <<"tools/call">>, #{name => ?TEAM, arguments => #{}})),
        true = port_command(Port, <<"{bad json}\n">>),
        ?assertMatch(#{<<"error">> := #{<<"code">> := -32700}}, response(Port)),
        ?assertMatch(#{<<"result">> := #{}}, rpc(Port, 5, <<"ping">>, #{}))
    after
        try port_close(Port) catch error:badarg -> ok end
    end.

rpc(Port, Id, Method, Params) ->
    send(Port, #{id => Id, method => Method, params => Params}),
    #{<<"id">> := Id, <<"jsonrpc">> := <<"2.0">>} = Reply = response(Port),
    Reply.

send(Port, Message) ->
    true = port_command(Port, [json:encode(Message#{jsonrpc => <<"2.0">>}), $\n]).

response(Port) ->
    receive
        {Port, {data, {eol, Line}}} -> json:decode(Line);
        {Port, {exit_status, Status}} -> error({server_exit, Status})
    after 10000 -> error(mcp_response_timeout)
    end.

