%% Feature: normalizing team names, dates and numbers
-module(soccer_util_tests).
-include_lib("eunit/include/eunit.hrl").

%% Scenario: state suffixes are removed from team names
%%   Given team names with a state suffix in the three spellings used by the data
%%   When they are normalized
%%   Then the suffix is gone and the name is kept
team_name_suffix_test() ->
    ?assertEqual(<<"Palmeiras">>, soccer_util:team_name(<<"Palmeiras-SP">>)),
    ?assertEqual(<<"Palmeiras">>, soccer_util:team_name(<<"Palmeiras - SP">>)),
    ?assertEqual(<<"Barcelona">>, soccer_util:team_name(<<"Barcelona-EQU">>)).

%% Scenario: parenthetical notes are removed
%%   Given a Copa do Brasil team name with an old-name note and a state
%%   When it is normalized
%%   Then only the club name remains
team_name_parenthetical_test() ->
    ?assertEqual(<<"Boavista Sport Club">>,
                 soccer_util:team_name(<<"Boavista Sport Club (antigo Esporte Clube Barreira) - RJ">>)),
    ?assertEqual(<<"Nacional">>, soccer_util:team_name(<<"Nacional (URU)">>)).

%% Scenario: accents are ignored when matching
%%   Given "São Paulo" and "Sao Paulo"
%%   When both are tokenized
%%   Then the tokens are identical
accent_insensitive_tokens_test() ->
    ?assertEqual([<<"sao">>, <<"paulo">>], soccer_util:tokens(<<"São Paulo"/utf8>>)),
    ?assertEqual(soccer_util:tokens(<<"São Paulo"/utf8>>), soccer_util:tokens(<<"Sao Paulo">>)),
    ?assertEqual([<<"gremio">>], soccer_util:tokens(<<"Grêmio"/utf8>>)).

%% Scenario: all date formats in the data
%%   Given ISO dates with and without time, and Brazilian DD/MM/YYYY dates
%%   When they are parsed
%%   Then each becomes the same YYYYMMDD integer for the same day
date_formats_test() ->
    ?assertEqual({ok, 20230924}, soccer_util:parse_date(<<"2023-09-24">>)),
    ?assertEqual({ok, 20120519}, soccer_util:parse_date(<<"2012-05-19 18:30:00">>)),
    ?assertEqual({ok, 20030329}, soccer_util:parse_date(<<"29/03/2003">>)),
    ?assertEqual(error, soccer_util:parse_date(<<"not a date">>)),
    ?assertEqual(error, soccer_util:parse_date(<<"2023-13-01">>)),
    ?assertEqual(<<"2023-09-24">>, soccer_util:format_date(20230924)).

%% Scenario: numbers in the data
%%   Given integer, float-formatted and empty goal values
%%   When they are parsed
%%   Then floats are truncated and empty values are undefined
number_parsing_test() ->
    ?assertEqual(2, soccer_util:parse_number(<<"2">>)),
    ?assertEqual(1, soccer_util:parse_number(<<"1.0">>)),
    ?assertEqual(undefined, soccer_util:parse_number(<<>>)),
    ?assertEqual(undefined, soccer_util:parse_number(<<"€5M"/utf8>>)).

%% Scenario: club name variants resolve to one canonical club
%%   Given the same club written as "Gremio-RS", "Gremio" and "Grêmio"
%%   When each is resolved
%%   Then all three share the canonical display name
%%   And Atlético-MG and Athletico-PR stay different clubs
club_variants_test() ->
    Name = fun(Raw) -> element(1, soccer_teams:resolve(Raw)) end,
    ?assertEqual(Name(<<"Grêmio"/utf8>>), Name(<<"Gremio-RS">>)),
    ?assertEqual(Name(<<"Gremio">>), Name(<<"Gremio-RS">>)),
    ?assertEqual(Name(<<"Atletico-MG">>), Name(<<"Atletico Mineiro">>)),
    ?assertEqual(Name(<<"Athletico Paranaense">>), Name(<<"Atlético - PR"/utf8>>)),
    ?assertNotEqual(Name(<<"Atletico-MG">>), Name(<<"Atletico-PR">>)).
