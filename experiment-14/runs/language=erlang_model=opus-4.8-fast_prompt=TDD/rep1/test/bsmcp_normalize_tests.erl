-module(bsmcp_normalize_tests).
-include_lib("eunit/include/eunit.hrl").

%% normalize/1 produces a canonical matching key (lowercase, accent-free,
%% no state/country suffix).

plain_name_test() ->
    ?assertEqual(<<"flamengo">>, bsmcp_normalize:normalize(<<"Flamengo">>)).

strips_state_suffix_test() ->
    ?assertEqual(<<"palmeiras">>, bsmcp_normalize:normalize(<<"Palmeiras-SP">>)),
    ?assertEqual(<<"flamengo">>, bsmcp_normalize:normalize(<<"Flamengo-RJ">>)).

strips_spaced_state_suffix_test() ->
    %% Ambiguous club: the state code is part of the canonical key so that
    %% América-MG and América-RN stay distinct.
    ?assertEqual(<<"america-mg">>,
                 bsmcp_normalize:normalize(unicode:characters_to_binary("América - MG"))).

unambiguous_suffix_is_stripped_test() ->
    %% Non-ambiguous clubs keep the spec's "Palmeiras-SP" == "Palmeiras".
    ?assertEqual(<<"corinthians">>, bsmcp_normalize:normalize(<<"Corinthians-SP">>)).

%% --- alias canonicalization ------------------------------------------

ambiguous_atletico_kept_distinct_test() ->
    MG = bsmcp_normalize:normalize(unicode:characters_to_binary("Atlético-MG")),
    GO = bsmcp_normalize:normalize(unicode:characters_to_binary("Atlético-GO")),
    PR = bsmcp_normalize:normalize(<<"Athletico-PR">>),
    ?assertNotEqual(MG, GO),
    ?assertNotEqual(MG, PR),
    ?assertNotEqual(GO, PR).

full_name_matches_suffixed_atletico_test() ->
    ?assertEqual(bsmcp_normalize:normalize(unicode:characters_to_binary("Atlético-MG")),
                 bsmcp_normalize:normalize(<<"Atletico Mineiro">>)),
    ?assertEqual(bsmcp_normalize:normalize(<<"Athletico-PR">>),
                 bsmcp_normalize:normalize(<<"Atletico Paranaense">>)).

atletico_pr_spelling_variants_match_test() ->
    %% "Atletico-PR" (no h) and "Athletico-PR" are the same club.
    ?assertEqual(bsmcp_normalize:normalize(<<"Atletico-PR">>),
                 bsmcp_normalize:normalize(<<"Athletico-PR">>)).

full_name_prefix_matches_test() ->
    ?assertEqual(bsmcp_normalize:normalize(<<"Bahia-BA">>),
                 bsmcp_normalize:normalize(<<"EC Bahia">>)),
    ?assertEqual(bsmcp_normalize:normalize(<<"Vasco">>),
                 bsmcp_normalize:normalize(<<"Vasco Da Gama RJ">>)),
    ?assertEqual(bsmcp_normalize:normalize(<<"Red Bull Bragantino-SP">>),
                 bsmcp_normalize:normalize(<<"Bragantino">>)).

strips_country_paren_test() ->
    ?assertEqual(<<"nacional">>, bsmcp_normalize:normalize(<<"Nacional (URU)">>)).

strips_country_suffix_test() ->
    ?assertEqual(<<"barcelona">>, bsmcp_normalize:normalize(<<"Barcelona-EQU">>)).

removes_accents_test() ->
    ?assertEqual(<<"sao paulo">>,
                 bsmcp_normalize:normalize(unicode:characters_to_binary("São Paulo"))),
    ?assertEqual(<<"gremio">>,
                 bsmcp_normalize:normalize(unicode:characters_to_binary("Grêmio"))).

accented_and_unaccented_match_test() ->
    ?assertEqual(bsmcp_normalize:normalize(unicode:characters_to_binary("São Paulo")),
                 bsmcp_normalize:normalize(<<"Sao Paulo">>)).

suffix_and_plain_match_test() ->
    ?assertEqual(bsmcp_normalize:normalize(<<"Palmeiras-SP">>),
                 bsmcp_normalize:normalize(<<"Palmeiras">>)).

same_team_test() ->
    ?assert(bsmcp_normalize:same_team(<<"Palmeiras-SP">>,
                                      unicode:characters_to_binary("Palmeiras"))),
    ?assertNot(bsmcp_normalize:same_team(<<"Palmeiras">>, <<"Santos">>)).

display_name_strips_suffix_keeps_accents_test() ->
    %% display_name normalizes the suffix away but keeps human-readable accents
    ?assertEqual(unicode:characters_to_binary("São Paulo"),
                 bsmcp_normalize:display_name(<<"São Paulo-SP"/utf8>>)).

display_keeps_suffix_for_ambiguous_club_test() ->
    %% Ambiguous clubs keep their state code in the display name so the
    %% three Atléticos are distinguishable in output.
    ?assertEqual(<<"Atlético-MG"/utf8>>,
                 bsmcp_normalize:display_name(<<"Atlético-MG"/utf8>>)),
    ?assertEqual(<<"Palmeiras">>, bsmcp_normalize:display_name(<<"Palmeiras-SP">>)).

trims_whitespace_test() ->
    ?assertEqual(<<"santos">>, bsmcp_normalize:normalize(<<"  Santos  ">>)).
