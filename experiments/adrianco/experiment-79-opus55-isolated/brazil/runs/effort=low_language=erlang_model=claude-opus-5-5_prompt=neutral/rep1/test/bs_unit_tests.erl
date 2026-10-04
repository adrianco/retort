%% Unit scenarios for the building blocks that need no dataset:
%% CSV parsing, date parsing and team-name classification.
-module(bs_unit_tests).
-include_lib("eunit/include/eunit.hrl").

%% Scenario: CSV with quotes, embedded commas, escaped quotes, CRLF and BOM
csv_quoted_fields_test() ->
    Csv = <<16#EF, 16#BB, 16#BF, "a,b,c\r\n\"x, y\",\"say \"\"hi\"\"\",3\r\n,,\n1,2,3">>,
    ?assertEqual([[<<"a">>, <<"b">>, <<"c">>],
                  [<<"x, y">>, <<"say \"hi\"">>, <<"3">>],
                  [<<>>, <<>>, <<>>],
                  [<<"1">>, <<"2">>, <<"3">>]], bs_csv:parse(Csv)).

csv_maps_pad_short_rows_test() ->
    ?assertEqual([#{<<"a">> => <<"1">>, <<"b">> => <<>>}], bs_csv:parse_maps(<<"a,b\n1\n">>)),
    ?assertEqual([], bs_csv:parse_maps(<<>>)).

%% Scenario: the three date formats found in the datasets
date_formats_test() ->
    ?assertEqual({2023, 9, 24}, bs_data:parse_date(<<"2023-09-24">>)),
    ?assertEqual({2003, 3, 29}, bs_data:parse_date(<<"29/03/2003">>)),
    ?assertEqual({2012, 5, 19}, bs_data:parse_date(<<"2012-05-19 18:30:00">>)),
    ?assertEqual(undefined, bs_data:parse_date(<<"NA">>)),
    ?assertEqual(undefined, bs_data:parse_date(<<"2023-02-31">>)).

%% Scenario: accents and case are folded
fold_test() ->
    ?assertEqual(<<"sao paulo">>, bs_team:fold(<<"São  Paulo"/utf8>>)),
    ?assertEqual(<<"gremio">>, bs_team:fold(<<"GRÊMIO"/utf8>>)),
    ?assertEqual(<<"avai">>, bs_team:fold(<<"Avaí"/utf8>>)).

%% Scenario: every spelling of a club maps to one key
name_variations_test_() ->
    Same = fun(Key, Names) ->
                   [?_assertEqual({N, {club, Key}}, {N, bs_team:classify(N)}) || N <- Names]
           end,
    [Same(<<"palmeiras">>, [<<"Palmeiras-SP">>, <<"Palmeiras - SP">>, <<"Palmeiras">>, <<"palmeiras">>]),
     Same(<<"sao paulo">>, [<<"Sao Paulo-SP">>, <<"São Paulo - SP"/utf8>>, <<"São Paulo"/utf8>>,
                            <<"Sao Paulo">>, <<"São Paulo FC"/utf8>>]),
     Same(<<"corinthians">>, [<<"Corinthians-SP">>, <<"Sport Club Corinthians Paulista">>]),
     Same(<<"atletico-mg">>, [<<"Atletico-MG">>, <<"Atlético - MG"/utf8>>, <<"Atlético Mineiro"/utf8>>,
                              <<"Atletico Mineiro">>]),
     Same(<<"athletico-pr">>, [<<"Atletico-PR">>, <<"Athletico-PR">>, <<"Athletico Paranaense - PR">>,
                               <<"Athletico">>, <<"Atlético Paranaense"/utf8>>]),
     Same(<<"america-mg">>, [<<"America MG">>, <<"América - MG"/utf8>>, <<"América FC (Minas Gerais)"/utf8>>]),
     Same(<<"vasco">>, [<<"Vasco da Gama-RJ">>, <<"Vasco Da Gama RJ">>, <<"Vasco">>]),
     Same(<<"fortaleza">>, [<<"Fortaleza Esporte Clube">>, <<"Fortaleza EC">>, <<"Fortaleza-CE">>])].

%% Scenario: homonyms from another state stay separate clubs
homonyms_test() ->
    ?assertMatch({uf, <<"flamengo">>, _, <<"pi">>}, bs_team:classify(<<"Flamengo - PI">>)),
    ?assertMatch({uf, <<"santos">>, _, <<"ap">>}, bs_team:classify(<<"Santos AP">>)),
    ?assertMatch({uf, <<"nacional">>, _, <<"uru">>}, bs_team:classify(<<"Nacional (URU)">>)),
    ?assertMatch({bare, <<"colo-colo">>, _}, bs_team:classify(<<"Colo-Colo">>)).

competition_and_stage_parsing_test() ->
    ?assertEqual(serie_a, bs_query:parse_competition(<<"Brasileirão"/utf8>>)),
    ?assertEqual(serie_a, bs_query:parse_competition(<<"Serie A">>)),
    ?assertEqual(copa_do_brasil, bs_query:parse_competition(<<"copa do brasil">>)),
    ?assertEqual(libertadores, bs_query:parse_competition(<<"Copa Libertadores">>)),
    ?assertEqual(serie_b, bs_query:parse_competition(<<"Série B"/utf8>>)),
    ?assertEqual(undefined, bs_query:parse_competition(<<"premier">>)),
    ?assertEqual(<<"final">>, bs_query:parse_stage(<<"Finals">>)),
    ?assertEqual(<<"semifinals">>, bs_query:parse_stage(<<"semi-final">>)).

%% Scenario: standings arithmetic on a hand-made set of matches
standings_from_matches_test() ->
    M = fun(H, Hg, Ag, A) -> #{home => H, away => A, hg => Hg, ag => Ag} end,
    Ms = [M(a, 2, 0, b), M(b, 1, 1, c), M(c, 0, 3, a), M(a, undefined, undefined, c)],
    ?assertMatch([{a, #{points := 6, matches := 2, gf := 5, ga := 0}},
                  {b, #{points := 1, gf := 1, ga := 3}},      % goal difference -2
                  {c, #{points := 1, gf := 1, ga := 4}}], bs_query:standings(Ms)),
    ?assertMatch(#{matches := 1, wins := 1}, bs_query:record(a, Ms, home)),
    ?assertMatch(#{matches := 3, goals := 7, home_wins := 1, draws := 1, away_wins := 1},
                 bs_query:league_stats(Ms)).
