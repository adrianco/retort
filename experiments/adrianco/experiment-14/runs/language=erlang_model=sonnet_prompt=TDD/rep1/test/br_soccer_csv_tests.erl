-module(br_soccer_csv_tests).
-include_lib("eunit/include/eunit.hrl").

%% TDD Cycle 1: Basic CSV line parsing
parse_simple_line_test() ->
    Line = <<"hello,world,foo">>,
    ?assertEqual([<<"hello">>, <<"world">>, <<"foo">>],
                 br_soccer_csv:parse_line(Line)).

parse_quoted_field_test() ->
    Line = <<"\"hello world\",foo,bar">>,
    ?assertEqual([<<"hello world">>, <<"foo">>, <<"bar">>],
                 br_soccer_csv:parse_line(Line)).

parse_quoted_with_comma_test() ->
    Line = <<"\"hello, world\",foo">>,
    ?assertEqual([<<"hello, world">>, <<"foo">>],
                 br_soccer_csv:parse_line(Line)).

parse_empty_field_test() ->
    Line = <<"a,,b">>,
    ?assertEqual([<<"a">>, <<>>, <<"b">>],
                 br_soccer_csv:parse_line(Line)).

%% TDD Cycle 2: Headers and rows into maps
parse_csv_string_test() ->
    Csv = <<"name,age\nAlice,30\nBob,25">>,
    Expected = [
        #{<<"name">> => <<"Alice">>, <<"age">> => <<"30">>},
        #{<<"name">> => <<"Bob">>, <<"age">> => <<"25">>}
    ],
    ?assertEqual(Expected, br_soccer_csv:parse_string(Csv)).

parse_csv_with_quotes_test() ->
    Csv = <<"team,city\n\"Sao Paulo FC\",\"Sao Paulo\"">>,
    Expected = [
        #{<<"team">> => <<"Sao Paulo FC">>, <<"city">> => <<"Sao Paulo">>}
    ],
    ?assertEqual(Expected, br_soccer_csv:parse_string(Csv)).

parse_csv_ignores_empty_lines_test() ->
    Csv = <<"name,age\nAlice,30\n\nBob,25\n">>,
    Expected = [
        #{<<"name">> => <<"Alice">>, <<"age">> => <<"30">>},
        #{<<"name">> => <<"Bob">>, <<"age">> => <<"25">>}
    ],
    ?assertEqual(Expected, br_soccer_csv:parse_string(Csv)).

%% TDD Cycle 3: Team name normalization
normalize_team_with_state_test() ->
    ?assertEqual(<<"Palmeiras">>, br_soccer_csv:normalize_team(<<"Palmeiras-SP">>)).

normalize_team_without_state_test() ->
    ?assertEqual(<<"Flamengo">>, br_soccer_csv:normalize_team(<<"Flamengo">>)).

normalize_team_rj_suffix_test() ->
    ?assertEqual(<<"Flamengo">>, br_soccer_csv:normalize_team(<<"Flamengo-RJ">>)).

normalize_team_lowercase_test() ->
    ?assertEqual(<<"flamengo">>, br_soccer_csv:normalize_team(<<"flamengo">>)).

%% TDD Cycle 4: Date parsing
parse_date_iso_test() ->
    ?assertEqual({2023, 9, 24}, br_soccer_csv:parse_date(<<"2023-09-24">>)).

parse_date_with_time_test() ->
    ?assertEqual({2012, 5, 19}, br_soccer_csv:parse_date(<<"2012-05-19 18:30:00">>)).

parse_date_brazilian_format_test() ->
    ?assertEqual({2003, 3, 29}, br_soccer_csv:parse_date(<<"29/03/2003">>)).

parse_date_invalid_test() ->
    ?assertEqual(undefined, br_soccer_csv:parse_date(<<"not-a-date">>)).
