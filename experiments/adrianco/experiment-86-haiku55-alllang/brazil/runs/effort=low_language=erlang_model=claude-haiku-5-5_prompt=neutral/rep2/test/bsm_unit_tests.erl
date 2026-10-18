%% Unit tests for the low-level parsing helpers: CSV, text folding, dates, team names.
-module(bsm_unit_tests).
-include_lib("eunit/include/eunit.hrl").

%% --- CSV -------------------------------------------------------------------

csv_test_() ->
    [
     {"plain rows are split on commas",
      ?_assertEqual([[<<"a">>, <<"b">>], [<<"1">>, <<"2">>]], bsm_csv:parse(<<"a,b\n1,2\n">>))},
     {"quoted fields may contain commas and newlines",
      ?_assertEqual([[<<"x,y">>, <<"line1\nline2">>]], bsm_csv:parse(<<"\"x,y\",\"line1\nline2\"\n">>))},
     {"doubled quotes become a single quote",
      ?_assertEqual([[<<"say \"hi\"">>]], bsm_csv:parse(<<"\"say \"\"hi\"\"\"\n">>))},
     {"CRLF line endings are handled",
      ?_assertEqual([[<<"a">>, <<"b">>], [<<"c">>, <<"d">>]], bsm_csv:parse(<<"a,b\r\nc,d\r\n">>))},
     {"a UTF-8 byte order mark is ignored",
      ?_assertEqual([[<<"h">>]], bsm_csv:parse(<<16#EF, 16#BB, 16#BF, "h\n">>))},
     {"blank lines are skipped",
      ?_assertEqual([[<<"a">>], [<<"b">>]], bsm_csv:parse(<<"a\n\nb\n">>))},
     {"empty trailing fields are kept",
      ?_assertEqual([[<<"a">>, <<>>, <<>>]], bsm_csv:parse(<<"a,,\n">>))},
     {"rows_as_maps keys values by header and drops ragged rows",
      ?_assertEqual([#{<<"id">> => <<"1">>, <<"name">> => <<"Ana">>}],
                    bsm_csv:rows_as_maps(<<"id,name\n1,Ana\n2\n">>))}
    ].

%% --- Text ------------------------------------------------------------------

text_test_() ->
    [
     {"fold strips accents and case",
      ?_assertEqual(<<"sao paulo">>, bsm_text:fold(<<"São Paulo"/utf8>>))},
     {"fold collapses whitespace",
      ?_assertEqual(<<"sport club">>, bsm_text:fold(<<"  Sport   Club ">>))},
     {"contains ignores case and accents",
      ?_assert(bsm_text:contains(<<"Grêmio"/utf8>>, <<"GREMIO">>))},
     {"an empty needle always matches",
      ?_assert(bsm_text:contains(<<"anything">>, <<>>))},
     {"parse_int accepts integers and float strings",
      ?_assertEqual([2, 1, 0], [bsm_text:parse_int(B) || B <- [<<"2">>, <<"1.0">>, <<" 0 ">>]])},
     {"parse_int returns undefined for non-numbers",
      ?_assertEqual(undefined, bsm_text:parse_int(<<"REMARCADO">>))}
    ].

%% --- Dates -----------------------------------------------------------------

date_test_() ->
    [
     {"ISO date with time is reduced to the date",
      ?_assertEqual({ok, <<"2012-05-19">>}, bsm_date:parse(<<"2012-05-19 18:30:00">>))},
     {"Brazilian DD/MM/YYYY is converted to ISO",
      ?_assertEqual({ok, <<"2003-03-29">>}, bsm_date:parse(<<"29/03/2003">>))},
     {"impossible months are rejected",
      ?_assertEqual(error, bsm_date:parse(<<"2003-13-01">>))},
     {"garbage is rejected",
      ?_assertEqual(error, bsm_date:parse(<<"not a date">>))}
    ].

%% --- Team names ------------------------------------------------------------

team_test_() ->
    [
     {"a trailing state suffix is split off",
      ?_assertEqual(#{name => <<"Palmeiras">>, base => <<"palmeiras">>, state => <<"SP">>},
                    bsm_team:parse(<<"Palmeiras-SP">>))},
     {"a space-separated state is recognised",
      ?_assertEqual(#{name => <<"Botafogo">>, base => <<"botafogo">>, state => <<"RJ">>},
                    bsm_team:parse(<<"Botafogo RJ">>))},
     {"a dash with spaces and a parenthetical are removed",
      ?_assertEqual(#{name => <<"Boavista Sport Club">>,
                      base => <<"boavista sport">>, state => <<"RJ">>},
                    bsm_team:parse(<<"Boavista Sport Club (antigo Esporte Clube Barreira) - RJ"/utf8>>))},
     {"country codes in parentheses are dropped",
      ?_assertEqual(<<"nacional">>, maps:get(base, bsm_team:parse(<<"Nacional (URU)">>)))},
     {"club abbreviations at either end are ignored",
      ?_assertEqual(<<"bahia">>, maps:get(base, bsm_team:parse(<<"EC Bahia">>)))},
     {"club abbreviations are not mistaken for states",
      ?_assertEqual(<<>>, maps:get(state, bsm_team:parse(<<"Brasilia FC">>)))},
     {"full names resolve to short names",
      ?_assertEqual(<<"corinthians">>,
                    maps:get(base, bsm_team:parse(<<"Sport Club Corinthians Paulista">>)))},
     {"Athletico and Atlético Paranaense are the same club",
      ?_assertEqual({<<"atletico">>, <<"PR">>},
                    begin T = bsm_team:parse(<<"Athletico Paranaense">>),
                          {maps:get(base, T), maps:get(state, T)} end)},
     {"accented and unaccented names match",
      ?_assert(bsm_team:same(bsm_team:parse(<<"Grêmio"/utf8>>), bsm_team:parse(<<"Gremio">>)))},
     {"same clubs in different states do not match",
      ?_assertNot(bsm_team:same(bsm_team:parse(<<"Atletico-MG">>), bsm_team:parse(<<"Atletico-PR">>)))},
     {"an unknown state matches any state",
      ?_assert(bsm_team:same(bsm_team:parse(<<"Flamengo">>), bsm_team:parse(<<"Flamengo-RJ">>)))},
     {"an unrecognised two-letter state code is treated as unknown",
      ?_assertEqual(<<>>, maps:get(state, bsm_team:parse(<<"Bahia-BH">>)))}
    ].
