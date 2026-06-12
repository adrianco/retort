-module(br_soccer_csv_tests).
-include_lib("eunit/include/eunit.hrl").

parse_line_simple_test() ->
    ?assertEqual(["a", "b", "c"], br_soccer_csv:parse_line("a,b,c")).

parse_line_quoted_test() ->
    ?assertEqual(["hello world", "b", "c"], br_soccer_csv:parse_line("\"hello world\",b,c")).

parse_line_quoted_comma_test() ->
    ?assertEqual(["a,b", "c"], br_soccer_csv:parse_line("\"a,b\",c")).

parse_line_empty_field_test() ->
    ?assertEqual(["a", "", "c"], br_soccer_csv:parse_line("a,,c")).

parse_line_numeric_test() ->
    ?assertEqual(["1", "2.5", "abc"], br_soccer_csv:parse_line("1,2.5,abc")).

strip_bom_test() ->
    ?assertEqual("hello", br_soccer_csv:strip_bom("\xEF\xBB\xBFhello")).

strip_bom_no_bom_test() ->
    ?assertEqual("hello", br_soccer_csv:strip_bom("hello")).

normalize_team_simple_test() ->
    ?assertEqual("Palmeiras", br_soccer_csv:normalize_team("Palmeiras-SP")).

normalize_team_no_suffix_test() ->
    ?assertEqual("Flamengo", br_soccer_csv:normalize_team("Flamengo")).

normalize_team_dash_in_name_test() ->
    ?assertEqual("Boavista Sport Club (antigo Esporte Clube Barreira)",
                 br_soccer_csv:normalize_team("Boavista Sport Club (antigo Esporte Clube Barreira) - RJ")).

parse_date_iso_test() ->
    ?assertEqual({2023, 9, 24}, br_soccer_csv:parse_date("2023-09-24")).

parse_date_iso_with_time_test() ->
    ?assertEqual({2012, 5, 19}, br_soccer_csv:parse_date("2012-05-19 18:30:00")).

parse_date_brazilian_test() ->
    ?assertEqual({2003, 3, 29}, br_soccer_csv:parse_date("29/03/2003")).

parse_int_test() ->
    ?assertEqual(3, br_soccer_csv:parse_int("3")),
    ?assertEqual(0, br_soccer_csv:parse_int("0")),
    ?assertEqual(0, br_soccer_csv:parse_int("")).

parse_float_test() ->
    ?assertEqual(2.5, br_soccer_csv:parse_float("2.5")),
    ?assertEqual(1.0, br_soccer_csv:parse_float("1.0")),
    ?assertEqual(0.0, br_soccer_csv:parse_float("")).
