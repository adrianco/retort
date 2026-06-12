-module(bsmcp_data_tests).
-include_lib("eunit/include/eunit.hrl").

%% --- date parsing -----------------------------------------------------

parse_date_iso_with_time_test() ->
    ?assertEqual(<<"2012-05-19">>, bsmcp_data:parse_date(<<"2012-05-19 18:30:00">>)).

parse_date_iso_plain_test() ->
    ?assertEqual(<<"2023-09-24">>, bsmcp_data:parse_date(<<"2023-09-24">>)).

parse_date_brazilian_test() ->
    ?assertEqual(<<"2003-03-29">>, bsmcp_data:parse_date(<<"29/03/2003">>)).

parse_date_empty_test() ->
    ?assertEqual(undefined, bsmcp_data:parse_date(<<>>)).

%% --- int parsing ------------------------------------------------------

parse_int_plain_test() ->
    ?assertEqual(3, bsmcp_data:parse_int(<<"3">>)).

parse_int_float_text_test() ->
    ?assertEqual(1, bsmcp_data:parse_int(<<"1.0">>)).

parse_int_empty_test() ->
    ?assertEqual(undefined, bsmcp_data:parse_int(<<>>)).

%% --- per-file row transforms -----------------------------------------

brasileirao_row_test() ->
    Row = #{<<"datetime">> => <<"2012-05-19 18:30:00">>,
            <<"home_team">> => <<"Palmeiras-SP">>,
            <<"home_team_state">> => <<"SP">>,
            <<"away_team">> => <<"Portuguesa-SP">>,
            <<"away_team_state">> => <<"SP">>,
            <<"home_goal">> => <<"1">>,
            <<"away_goal">> => <<"1">>,
            <<"season">> => <<"2012">>,
            <<"round">> => <<"1">>},
    M = bsmcp_data:brasileirao_row(Row),
    ?assertEqual(<<"Brasileirão"/utf8>>, maps:get(competition, M)),
    ?assertEqual(<<"Palmeiras">>, maps:get(home, M)),
    ?assertEqual(<<"palmeiras">>, maps:get(home_norm, M)),
    ?assertEqual(<<"Portuguesa">>, maps:get(away, M)),
    ?assertEqual(1, maps:get(home_goal, M)),
    ?assertEqual(1, maps:get(away_goal, M)),
    ?assertEqual(2012, maps:get(season, M)),
    ?assertEqual(<<"2012-05-19">>, maps:get(date, M)).

cup_row_test() ->
    Row = #{<<"round">> => <<"1">>,
            <<"datetime">> => <<"2012-03-07 16:00:00">>,
            <<"home_team">> => <<"Boavista - RJ">>,
            <<"away_team">> => <<"América - MG"/utf8>>,
            <<"home_goal">> => <<"0">>,
            <<"away_goal">> => <<"0">>,
            <<"season">> => <<"2012">>},
    M = bsmcp_data:cup_row(Row),
    ?assertEqual(<<"Copa do Brasil"/utf8>>, maps:get(competition, M)),
    ?assertEqual(<<"america-mg">>, maps:get(away_norm, M)),
    ?assertEqual(2012, maps:get(season, M)).

libertadores_row_test() ->
    Row = #{<<"datetime">> => <<"2013-02-12 20:15:00">>,
            <<"home_team">> => <<"Nacional (URU)">>,
            <<"away_team">> => <<"Barcelona-EQU">>,
            <<"home_goal">> => <<"2">>,
            <<"away_goal">> => <<"2">>,
            <<"season">> => <<"2013">>,
            <<"stage">> => <<"group stage">>},
    M = bsmcp_data:libertadores_row(Row),
    ?assertEqual(<<"Libertadores">>, maps:get(competition, M)),
    ?assertEqual(<<"nacional">>, maps:get(home_norm, M)),
    ?assertEqual(<<"barcelona">>, maps:get(away_norm, M)),
    ?assertEqual(<<"group stage">>, maps:get(stage, M)).

br_football_row_test() ->
    Row = #{<<"tournament">> => <<"Copa do Brasil"/utf8>>,
            <<"home">> => <<"Sao Paulo">>,
            <<"away">> => <<"Flamengo">>,
            <<"home_goal">> => <<"1.0">>,
            <<"away_goal">> => <<"1.0">>,
            <<"date">> => <<"2023-09-24">>,
            <<"home_shots">> => <<"8.0">>,
            <<"away_shots">> => <<"13.0">>},
    M = bsmcp_data:br_football_row(Row),
    ?assertEqual(<<"sao paulo">>, maps:get(home_norm, M)),
    ?assertEqual(1, maps:get(home_goal, M)),
    ?assertEqual(<<"2023-09-24">>, maps:get(date, M)),
    ?assertEqual(2023, maps:get(season, M)).

dm(Comp, Home, Away, Date) ->
    #{competition => Comp, home => Home, away => Away,
      home_norm => bsmcp_normalize:normalize(Home),
      away_norm => bsmcp_normalize:normalize(Away),
      home_goal => 1, away_goal => 0, season => 2019,
      round => undefined, date => Date, stage => undefined}.

dedup_removes_same_fixture_across_files_test() ->
    %% Same date + teams from two source files collapses to one, keeping
    %% the first (richer, canonically-named) occurrence.
    Ms = [dm(<<"Brasileirão"/utf8>>, <<"Flamengo">>, <<"Santos">>, <<"2019-06-01">>),
          dm(<<"Serie A">>, <<"Flamengo-RJ">>, <<"Santos">>, <<"2019-06-01">>)],
    [Only] = bsmcp_data:dedup(Ms),
    ?assertEqual(<<"Brasileirão"/utf8>>, maps:get(competition, Only)).

dedup_keeps_distinct_fixtures_test() ->
    Ms = [dm(<<"X">>, <<"Flamengo">>, <<"Santos">>, <<"2019-06-01">>),
          dm(<<"X">>, <<"Flamengo">>, <<"Santos">>, <<"2019-06-08">>),
          dm(<<"X">>, <<"Santos">>, <<"Flamengo">>, <<"2019-06-01">>)],
    ?assertEqual(3, length(bsmcp_data:dedup(Ms))).

dedup_keeps_dateless_matches_test() ->
    Ms = [dm(<<"X">>, <<"A">>, <<"B">>, undefined),
          dm(<<"X">>, <<"A">>, <<"B">>, undefined)],
    ?assertEqual(2, length(bsmcp_data:dedup(Ms))).

novo_row_test() ->
    Row = #{<<"ID">> => <<"2003.01.0001">>,
            <<"Data">> => <<"29/03/2003">>,
            <<"Ano">> => <<"2003">>,
            <<"Rodada">> => <<"1">>,
            <<"Equipe_mandante">> => <<"Guarani">>,
            <<"Equipe_visitante">> => <<"Vasco">>,
            <<"Gols_mandante">> => <<"4">>,
            <<"Gols_visitante">> => <<"2">>,
            <<"Mandante_UF">> => <<"SP">>,
            <<"Visitante_UF">> => <<"RJ">>,
            <<"Vencedor">> => <<"Mandante">>,
            <<"Arena">> => <<"Brinco de Ouro">>},
    M = bsmcp_data:novo_row(Row),
    ?assertEqual(<<"Brasileirão"/utf8>>, maps:get(competition, M)),
    ?assertEqual(<<"guarani">>, maps:get(home_norm, M)),
    ?assertEqual(4, maps:get(home_goal, M)),
    ?assertEqual(2, maps:get(away_goal, M)),
    ?assertEqual(<<"2003-03-29">>, maps:get(date, M)),
    ?assertEqual(2003, maps:get(season, M)).
