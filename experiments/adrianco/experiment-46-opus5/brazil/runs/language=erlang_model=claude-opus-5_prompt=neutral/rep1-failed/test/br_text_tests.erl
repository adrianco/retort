%%%-------------------------------------------------------------------
%%% @doc Unit tests for the text normalisation used by every lookup.
%%%-------------------------------------------------------------------
-module(br_text_tests).

-include_lib("eunit/include/eunit.hrl").

normalize_folds_accents_test() ->
    ?assertEqual(<<"sao paulo">>, br_text:normalize(<<"São Paulo"/utf8>>)),
    ?assertEqual(<<"gremio">>, br_text:normalize(<<"Grêmio"/utf8>>)),
    ?assertEqual(<<"avai">>, br_text:normalize(<<"Avaí"/utf8>>)),
    ?assertEqual(<<"atletico mineiro">>, br_text:normalize(<<"Atlético Mineiro"/utf8>>)),
    ?assertEqual(<<"criciuma">>, br_text:normalize(<<"Criciúma"/utf8>>)),
    ?assertEqual(<<"confianca">>, br_text:normalize(<<"Confiança"/utf8>>)).

normalize_collapses_punctuation_test() ->
    ?assertEqual(<<"america mg">>, br_text:normalize(<<"América - MG"/utf8>>)),
    ?assertEqual(<<"a b c rn">>, br_text:normalize(<<"A.b.c. - RN">>)),
    ?assertEqual(<<"palmeiras sp">>, br_text:normalize(<<"  Palmeiras-SP  ">>)),
    ?assertEqual(<<>>, br_text:normalize(<<"   ">>)).

normalize_accepts_lists_and_atoms_test() ->
    ?assertEqual(<<"santos">>, br_text:normalize("Santos")),
    ?assertEqual(<<"santos">>, br_text:normalize(santos)),
    ?assertEqual(<<"2019">>, br_text:normalize(2019)).

decomposed_and_precomposed_agree_test() ->
    Precomposed = <<"São"/utf8>>,
    Decomposed = <<"Sa", 16#CC, 16#83, "o">>,   % S a + combining tilde + o
    ?assertEqual(br_text:normalize(Precomposed), br_text:normalize(Decomposed)).

slug_test() ->
    ?assertEqual(<<"ponte-preta">>, br_text:slug(<<"Ponte Preta">>)),
    ?assertEqual(<<"sao-paulo">>, br_text:slug(<<"São  Paulo"/utf8>>)).

contains_ignores_case_and_accents_test() ->
    ?assert(br_text:contains(<<"Grêmio Foot-Ball Porto Alegrense"/utf8>>, <<"gremio">>)),
    ?assert(br_text:contains(<<"Vasco da Gama">>, <<"VASCO">>)),
    ?assertNot(br_text:contains(<<"Santos">>, <<"santos fc">>)).

trim_test() ->
    ?assertEqual(<<"x">>, br_text:trim(<<"  \t x \r\n">>)),
    ?assertEqual(<<>>, br_text:trim(<<"\r\n">>)),
    ?assertEqual(<<"São Paulo"/utf8>>, br_text:trim(<<" São Paulo "/utf8>>)).

tokens_test() ->
    ?assertEqual([<<"vasco">>, <<"da">>, <<"gama">>], br_text:tokens(<<"Vasco da Gama">>)),
    ?assertEqual([], br_text:tokens(<<"">>)).

titlecase_test() ->
    ?assertEqual(<<"Ponte Preta">>, br_text:titlecase(<<"ponte preta">>)).

fold_accents_keeps_case_test() ->
    ?assertEqual(<<"Sao Paulo">>, br_text:fold_accents(<<"São Paulo"/utf8>>)),
    ?assertEqual(<<"GREMIO">>, br_text:fold_accents(<<"GRÊMIO"/utf8>>)).
