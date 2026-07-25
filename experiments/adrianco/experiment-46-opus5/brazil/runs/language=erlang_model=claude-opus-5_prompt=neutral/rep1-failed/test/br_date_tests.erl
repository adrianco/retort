%%%-------------------------------------------------------------------
%%% @doc Unit tests for the multi-format date parser.
%%%-------------------------------------------------------------------
-module(br_date_tests).

-include_lib("eunit/include/eunit.hrl").

iso_date_test() ->
    ?assertEqual({ok, {2023, 9, 24}}, br_date:parse_date(<<"2023-09-24">>)),
    ?assertEqual({ok, {2023, 9, 24}, undefined}, br_date:parse(<<"2023-09-24">>)).

iso_datetime_test() ->
    ?assertEqual({ok, {2012, 5, 19}, {18, 30, 0}}, br_date:parse(<<"2012-05-19 18:30:00">>)),
    ?assertEqual({ok, {2012, 5, 19}, {18, 30, 0}}, br_date:parse(<<"2012-05-19T18:30:00">>)).

brazilian_date_test() ->
    ?assertEqual({ok, {2003, 3, 29}}, br_date:parse_date(<<"29/03/2003">>)),
    ?assertEqual({ok, {2003, 12, 1}}, br_date:parse_date(<<"01/12/2003">>)),
    ?assertEqual({ok, {2003, 3, 29}, undefined}, br_date:parse(<<"29/03/2003">>)).

time_test() ->
    ?assertEqual({ok, {20, 0, 0}}, br_date:parse_time(<<"20:00:00">>)),
    ?assertEqual({ok, {20, 30, 0}}, br_date:parse_time(<<"20:30">>)),
    ?assertEqual(error, br_date:parse_time(<<"25:00:00">>)),
    ?assertEqual(error, br_date:parse_time(<<"">>)).

invalid_input_test() ->
    ?assertEqual(error, br_date:parse_date(<<"">>)),
    ?assertEqual(error, br_date:parse_date(<<"NA">>)),
    ?assertEqual(error, br_date:parse_date(<<"2023-13-01">>)),
    ?assertEqual(error, br_date:parse_date(<<"2023-02-30">>)),
    ?assertEqual(error, br_date:parse(<<"not a date">>)).

format_test() ->
    ?assertEqual(<<"2019-11-24">>, br_date:format({2019, 11, 24})),
    ?assertEqual(<<"2019-01-02">>, br_date:format({2019, 1, 2})),
    ?assertEqual(<<"unknown">>, br_date:format(undefined)),
    ?assertEqual(<<"2019-01-02 16:00:00">>,
                 br_date:format_datetime({2019, 1, 2}, {16, 0, 0})),
    ?assertEqual(<<"2019-01-02">>, br_date:format_datetime({2019, 1, 2}, undefined)).

round_trip_test() ->
    {ok, D} = br_date:parse_date(<<"29/03/2003">>),
    ?assertEqual(<<"2003-03-29">>, br_date:format(D)).

range_test() ->
    ?assert(br_date:in_range({2019, 6, 1}, {2019, 1, 1}, {2019, 12, 31})),
    ?assert(br_date:in_range({2019, 1, 1}, {2019, 1, 1}, undefined)),
    ?assert(br_date:in_range({2019, 1, 1}, undefined, {2019, 1, 1})),
    ?assertNot(br_date:in_range({2018, 12, 31}, {2019, 1, 1}, undefined)),
    ?assertNot(br_date:in_range(undefined, {2019, 1, 1}, undefined)).

sortable_days_test() ->
    ?assert(br_date:to_days({2019, 1, 2}) > br_date:to_days({2019, 1, 1})),
    ?assertEqual(0, br_date:to_days(undefined)).

year_test() ->
    ?assertEqual(2019, br_date:year({2019, 5, 1})),
    ?assertEqual(undefined, br_date:year(undefined)).
