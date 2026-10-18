%%% Feature: Team names, dates and numbers are normalised from messy source text.
-module(bs_text_tests).

-include_lib("eunit/include/eunit.hrl").
-import(bs_test_support, [u/1]).

%% Scenario: Team name variants are treated as the same club
normalize_team_test_() ->
    [?_assertEqual(<<"palmeiras">>, bs_text:normalize_team(<<"Palmeiras-SP">>)),
     ?_assertEqual(<<"palmeiras">>, bs_text:normalize_team(<<"Palmeiras">>)),
     ?_assertEqual(u("gremio"), bs_text:normalize_team(u("Grêmio Foot-Ball Porto Alegrense"))),
     ?_assertEqual(<<"corinthians">>, bs_text:normalize_team(u("Sport Club Corinthians Paulista"))),
     ?_assertEqual(<<"sao paulo">>, bs_text:normalize_team(u("São Paulo"))),
     ?_assertEqual(<<"sao paulo">>, bs_text:normalize_team(u("Sao Paulo FC"))),
     ?_assertEqual(<<"fortaleza">>, bs_text:normalize_team(u("Fortaleza FC"))),
     ?_assertEqual(<<"nacional">>, bs_text:normalize_team(u("Nacional (URU)"))),
     ?_assertEqual(<<"boavista sport club">>,
                   bs_text:normalize_team(u("Boavista Sport Club (antigo Esporte Clube Barreira) - RJ")))].

%% Scenario: Team names carry their state so clubs sharing a name can be told apart
split_team_test_() ->
    [?_assertEqual({<<"atletico">>, <<"mg">>}, bs_text:split_team(u("Atlético-MG"))),
     ?_assertEqual({<<"atletico">>, <<"pr">>}, bs_text:split_team(<<"Athletico-PR">>)),
     ?_assertEqual({<<"vasco">>, <<"rj">>}, bs_text:split_team(u("Vasco Da Gama RJ"))),
     ?_assertEqual({<<"flamengo">>, none}, bs_text:split_team(<<"Flamengo">>)),
     ?_assertEqual({<<"avai">>, <<"sc">>}, bs_text:split_team(<<"Avai-SC">>)),
     ?_assertEqual({<<"barcelona-equ">>, none}, bs_text:split_team(<<"Barcelona-EQU">>))].

%% Scenario: Accents are removed for searching
fold_test_() ->
    [?_assertEqual("gremio", bs_text:fold(u("Grêmio"))),
     ?_assertEqual("avai", bs_text:fold(u("Avaí")))].

%% Scenario: ISO and Brazilian dates are both accepted
parse_date_test_() ->
    [?_assertEqual({ok, <<"2023-09-24">>}, bs_text:parse_date(<<"2023-09-24">>)),
     ?_assertEqual({ok, <<"2012-05-19">>}, bs_text:parse_date(<<"2012-05-19 18:30:00">>)),
     ?_assertEqual({ok, <<"2003-03-29">>}, bs_text:parse_date(<<"29/03/2003">>)),
     ?_assertEqual(error, bs_text:parse_date(<<"not a date">>))].

%% Scenario: Goals stored as floats or integers are read as integers
parse_int_test_() ->
    [?_assertEqual({ok, 2}, bs_text:parse_int(<<"2">>)),
     ?_assertEqual({ok, 1}, bs_text:parse_int(<<"1.0">>)),
     ?_assertEqual({ok, 3}, bs_text:parse_int(<<" 3 ">>)),
     ?_assertEqual(error, bs_text:parse_int(<<>>)),
     ?_assertEqual(error, bs_text:parse_int(<<"NA">>))].
