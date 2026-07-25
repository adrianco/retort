%%%-------------------------------------------------------------------
%%% @doc Unit tests for team name canonicalisation.
%%%
%%% These are the cases that decide whether data from five files with
%%% five naming conventions merges correctly - or silently merges two
%%% different clubs.
%%%-------------------------------------------------------------------
-module(br_names_tests).

-include_lib("eunit/include/eunit.hrl").

id(Name) -> br_names:canonical_id(Name).

%%--------------------------------------------------------------------
%% All spellings of one club collapse onto one id.
spelling_variants_test() ->
    Groups =
        [[<<"Palmeiras">>, <<"Palmeiras-SP">>, <<"Palmeiras - SP">>,
          <<"Sociedade Esportiva Palmeiras">>, <<"palmeiras">>],
         [<<"São Paulo"/utf8>>, <<"Sao Paulo">>, <<"Sao Paulo-SP">>, <<"São Paulo - SP"/utf8>>,
          <<"Sao Paulo Futebol Clube">>],
         [<<"Grêmio"/utf8>>, <<"Gremio">>, <<"Gremio RS">>, <<"Grêmio - RS"/utf8>>],
         [<<"Corinthians">>, <<"Corinthians-SP">>,
          <<"Sport Club Corinthians Paulista">>],
         [<<"Atletico Mineiro">>, <<"Atlético - MG"/utf8>>, <<"Atletico-MG">>,
          <<"Clube Atlético Mineiro"/utf8>>],
         [<<"Athletico Paranaense">>, <<"Atletico-PR">>, <<"Atlético Paranaense - PR"/utf8>>,
          <<"Athletico">>],
         [<<"Sport">>, <<"Sport-PE">>, <<"Sport Recife">>, <<"Sport Club do Recife">>],
         [<<"Vasco">>, <<"Vasco da Gama">>, <<"Vasco Da Gama RJ">>, <<"Vasco da Gama-RJ">>],
         [<<"Nautico">>, <<"Náutico - PE"/utf8>>, <<"Nautico Capibaribe">>],
         [<<"Ceara">>, <<"Ceará - CE"/utf8>>, <<"Ceará Sporting Club"/utf8>>]],
    [begin
         Ids = lists:usort([id(N) || N <- Group]),
         ?assertMatch({1, _}, {length(Ids), {Group, Ids}})
     end || Group <- Groups].

%%--------------------------------------------------------------------
%% Same short name, different clubs: the state must keep them apart.
homonymous_clubs_stay_apart_test() ->
    ?assertNotEqual(id(<<"América - MG"/utf8>>), id(<<"América - RN"/utf8>>)),
    ?assertNotEqual(id(<<"Flamengo-RJ">>), id(<<"Flamengo - PI">>)),
    ?assertNotEqual(id(<<"Atletico-MG">>), id(<<"Atletico-GO">>)),
    ?assertNotEqual(id(<<"Atletico-MG">>), id(<<"Atletico-PR">>)),
    ?assertNotEqual(id(<<"Botafogo-RJ">>), id(<<"Botafogo - PB">>)),
    ?assertNotEqual(id(<<"Santa Cruz - PE">>), id(<<"Santa Cruz - RN">>)),
    ?assertNotEqual(id(<<"Juventude - RS">>), id(<<"Juventude - MA">>)),
    ?assertNotEqual(id(<<"Santos - SP">>), id(<<"Santos - AP">>)),
    ?assertNotEqual(id(<<"Guarani - SP">>), id(<<"Guarani - CE">>)).

bare_name_maps_to_the_famous_club_test() ->
    ?assertEqual(<<"flamengo">>, id(<<"Flamengo">>)),
    ?assertEqual(<<"america-mg">>, id(<<"America MG">>)),
    ?assertEqual(<<"atletico-mg">>, id(<<"Atletico Mineiro">>)),
    ?assertEqual(<<"santos">>, id(<<"Santos">>)).

%%--------------------------------------------------------------------
%% International opponents in the Libertadores file.
country_codes_test() ->
    ?assertEqual(id(<<"Nacional (URU)">>), id(<<"Nacional-URU">>)),
    ?assertEqual(id(<<"Guaraní (PAR)"/utf8>>), id(<<"Guaraní-PAR"/utf8>>)),
    ?assertEqual(id(<<"Universitario (PER)">>), id(<<"Universitario-PER">>)),
    ?assertNotEqual(id(<<"Nacional (URU)">>), id(<<"Nacional (PAR)">>)),
    ?assertNotEqual(id(<<"River Plate">>), id(<<"River Plate-URU">>)),
    ?assertNotEqual(id(<<"Guaraní (PAR)"/utf8>>), id(<<"Guarani - SP">>)).

canonical_returns_state_and_country_test() ->
    ?assertMatch({<<"palmeiras">>, <<"Palmeiras">>, <<"SP">>, <<"BRA">>},
                 br_names:canonical(<<"Palmeiras-SP">>)),
    ?assertMatch({<<"boca-juniors">>, <<"Boca Juniors">>, undefined, <<"ARG">>},
                 br_names:canonical(<<"Boca Juniors">>)).

unknown_clubs_get_a_stable_id_test() ->
    ?assertEqual(id(<<"Aguia Negra-MS">>), id(<<"Águia Negra - MS"/utf8>>)),
    ?assertEqual(<<"tuna-luso">>, id(<<"Tuna Luso">>)),
    %% and never collide with a registered club
    ?assertNotEqual(id(<<"Flamengo">>), id(<<"Flamengo do Piauí - PI"/utf8>>)).

initials_are_joined_test() ->
    ?assertEqual(id(<<"C.s.a. - AL">>), id(<<"CSA">>)),
    ?assertEqual(id(<<"C.r.b. - AL">>), id(<<"CRB">>)),
    ?assertEqual(id(<<"A.b.c. - RN">>), id(<<"ABC - RN">>)).

affixes_are_stripped_test() ->
    ?assertEqual(<<"bahia">>, id(<<"EC Bahia">>)),
    ?assertEqual(<<"fortaleza">>, id(<<"Fortaleza EC">>)),
    ?assertEqual(<<"vitoria">>, id(<<"Vitoria EC">>)),
    ?assertEqual(<<"parana">>, id(<<"CA Parana">>)),
    %% but a name that is only an abbreviation survives
    ?assertEqual(<<"csa">>, id(<<"CSA">>)),
    ?assertEqual(<<"abc">>, id(<<"ABC - RN">>)).

split_region_test() ->
    ?assertEqual({<<"palmeiras">>, <<"SP">>}, br_names:split_region(<<"palmeiras sp">>)),
    ?assertEqual({<<"nacional">>, <<"URU">>}, br_names:split_region(<<"nacional uru">>)),
    ?assertEqual({<<"colo colo">>, undefined}, br_names:split_region(<<"colo colo">>)).

%%--------------------------------------------------------------------
competition_aliases_test() ->
    ?assertEqual(<<"brasileirao_serie_a">>, br_names:competition(<<"Brasileirao">>)),
    ?assertEqual(<<"brasileirao_serie_a">>, br_names:competition(<<"Serie A">>)),
    ?assertEqual(<<"brasileirao_serie_a">>, br_names:competition(<<"campeonato brasileiro">>)),
    ?assertEqual(<<"brasileirao_serie_b">>, br_names:competition(<<"serie b">>)),
    ?assertEqual(<<"copa_do_brasil">>, br_names:competition(<<"Copa do Brasil">>)),
    ?assertEqual(<<"libertadores">>, br_names:competition(<<"Copa Libertadores">>)),
    ?assertEqual(undefined, br_names:competition(<<"Champions League">>)).

competition_display_test() ->
    ?assertEqual(<<"Brasileirão Série A"/utf8>>,
                 br_names:competition_display(<<"brasileirao_serie_a">>)).

rivalries_test() ->
    ?assertEqual(<<"Fla-Flu">>, br_names:rivalry_of(<<"flamengo">>, <<"fluminense">>)),
    ?assertEqual(<<"Fla-Flu">>, br_names:rivalry_of(<<"fluminense">>, <<"flamengo">>)),
    ?assertEqual(<<"Gre-Nal">>, br_names:rivalry_of(<<"gremio">>, <<"internacional">>)),
    ?assertEqual(undefined, br_names:rivalry_of(<<"santos">>, <<"gremio">>)).

registry_ids_are_unique_test() ->
    Ids = [Id || {Id, _, _, _, _, _} <- br_names:registry()],
    ?assertEqual(lists:usort(Ids), lists:sort(Ids)).
