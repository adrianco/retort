-module(bsmcp_names_tests).
-include_lib("eunit/include/eunit.hrl").

%% --- Team name normalization across the conventions used by the datasets ---

state_suffix_test() ->
    ?assertEqual(<<"palmeiras">>, bsmcp_names:canonical(<<"Palmeiras-SP">>)),
    ?assertEqual(<<"palmeiras">>, bsmcp_names:canonical(<<"Palmeiras">>)).

accents_test() ->
    ?assertEqual(<<"sao paulo">>, bsmcp_names:canonical(<<"São Paulo - SP"/utf8>>)),
    ?assertEqual(<<"sao paulo">>, bsmcp_names:canonical(<<"Sao Paulo">>)),
    ?assertEqual(<<"gremio">>, bsmcp_names:canonical(<<"Grêmio - RS"/utf8>>)),
    ?assertEqual(<<"avai">>, bsmcp_names:canonical(<<"Avaí - SC"/utf8>>)).

full_name_alias_test() ->
    ?assertEqual(<<"corinthians">>,
                 bsmcp_names:canonical(<<"Sport Club Corinthians Paulista">>)),
    ?assertEqual(<<"corinthians">>, bsmcp_names:canonical(<<"Corinthians-SP">>)).

athletico_variants_test() ->
    Canon = bsmcp_names:canonical(<<"Athletico-PR">>),
    ?assertEqual(Canon, bsmcp_names:canonical(<<"Atletico-PR">>)),
    ?assertEqual(Canon, bsmcp_names:canonical(<<"Atlético Paranaense - PR"/utf8>>)).

parenthetical_dropped_test() ->
    %% the "(antigo ...)" aside is dropped; the state token is kept for
    %% unknown clubs (that's what disambiguates the two Américas)
    ?assertEqual(<<"boavista sport club rj">>,
                 bsmcp_names:canonical(
                   <<"Boavista Sport Club (antigo Esporte Clube Barreira) - RJ">>)).

ambiguous_americas_stay_distinct_test() ->
    ?assertNotEqual(bsmcp_names:canonical(<<"América - MG"/utf8>>),
                    bsmcp_names:canonical(<<"América - RN"/utf8>>)).

same_team_loose_test() ->
    ?assert(bsmcp_names:same_team(<<"ceara">>, <<"ceara ce">>)),
    ?assert(bsmcp_names:same_team(<<"fortaleza">>, <<"fortaleza fc">>)),
    ?assertNot(bsmcp_names:same_team(<<"gremio">>, <<"gremio novorizontino">>)).

%% --- Competition canonicalization ---

competition_test() ->
    ?assertEqual(<<"Brasileirão Série A"/utf8>>, bsmcp_names:competition(<<"brasileirao">>)),
    ?assertEqual(<<"Brasileirão Série A"/utf8>>, bsmcp_names:competition(<<"Serie A">>)),
    ?assertEqual(<<"Copa do Brasil">>, bsmcp_names:competition(<<"copa do brasil">>)),
    ?assertEqual(<<"Copa Libertadores">>, bsmcp_names:competition(<<"Libertadores">>)),
    ?assertEqual(<<"Série B"/utf8>>, bsmcp_names:competition(<<"série b"/utf8>>)),
    ?assertEqual(any, bsmcp_names:competition(undefined)),
    ?assertEqual(any, bsmcp_names:competition(<<"premier league">>)).

%% --- Date handling for the formats present in the data ---

iso_date_test() ->
    ?assertEqual({2023, 9, 24}, bsmcp_names:parse_date(<<"2023-09-24">>)).

iso_datetime_test() ->
    ?assertEqual({2012, 5, 19}, bsmcp_names:parse_date(<<"2012-05-19 18:30:00">>)).

brazilian_date_test() ->
    ?assertEqual({2003, 3, 29}, bsmcp_names:parse_date(<<"29/03/2003">>)).

bad_date_test() ->
    ?assertEqual(undefined, bsmcp_names:parse_date(<<"not a date">>)),
    ?assertEqual(undefined, bsmcp_names:parse_date(<<>>)).

format_date_test() ->
    ?assertEqual(<<"2019-11-24">>, bsmcp_names:format_date({2019, 11, 24})).
