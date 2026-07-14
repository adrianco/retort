%%% ===================================================================
%%% Brazilian Soccer MCP Server - normalisation unit tests
%%%
%%% Context: Finer-grained TDD for `bsoccer_norm', the team-name and
%%% text normalisation that lets bare queries ("Flamengo", "Sao Paulo")
%%% match the dataset spellings ("Flamengo-RJ", "São Paulo") while
%%% keeping genuinely different clubs (Atlético-MG vs Atlético-PR) apart.
%%% ===================================================================
-module(bsoccer_norm_tests).
-include_lib("eunit/include/eunit.hrl").

fold_lowercases_and_strips_accents_test() ->
    ?assertEqual(<<"sao paulo">>, bsoccer_norm:fold(<<"São Paulo"/utf8>>)),
    ?assertEqual(<<"gremio">>, bsoccer_norm:fold(<<"Grêmio"/utf8>>)),
    ?assertEqual(<<"atletico">>, bsoccer_norm:fold(<<"Atlético"/utf8>>)).

base_key_strips_state_suffix_test() ->
    ?assertEqual(<<"flamengo">>, bsoccer_norm:base_key(<<"Flamengo-RJ">>)),
    ?assertEqual(<<"flamengo">>, bsoccer_norm:base_key(<<"Flamengo">>)),
    ?assertEqual(<<"america">>, bsoccer_norm:base_key(<<"América - MG"/utf8>>)),
    ?assertEqual(<<"nacional">>, bsoccer_norm:base_key(<<"Nacional (URU)">>)).

bare_query_matches_suffixed_name_test() ->
    ?assert(bsoccer_norm:team_matches(<<"Flamengo">>, <<"Flamengo-RJ">>)),
    ?assert(bsoccer_norm:team_matches(<<"flamengo">>, <<"Flamengo-RJ">>)),
    ?assert(bsoccer_norm:team_matches(<<"Sao Paulo">>, <<"São Paulo-SP"/utf8>>)).

different_clubs_stay_distinct_test() ->
    %% A fully-qualified query keeps the two Atléticos apart.
    ?assert(bsoccer_norm:team_matches(<<"Atletico-MG">>, <<"Atlético-MG"/utf8>>)),
    ?assertNot(bsoccer_norm:team_matches(<<"Atletico-MG">>, <<"Atletico-PR">>)).

unrelated_names_do_not_match_test() ->
    ?assertNot(bsoccer_norm:team_matches(<<"Flamengo">>, <<"Fluminense">>)),
    ?assertNot(bsoccer_norm:team_matches(<<"Santos">>, <<"Palmeiras-SP">>)).

contains_fold_test() ->
    ?assert(bsoccer_norm:contains_fold(<<"Copa Libertadores">>, <<"libertadores">>)),
    ?assert(bsoccer_norm:contains_fold(<<"São Paulo FC"/utf8>>, <<"sao paulo">>)),
    ?assertNot(bsoccer_norm:contains_fold(<<"Brasileirão"/utf8>>, <<"libertadores">>)).
