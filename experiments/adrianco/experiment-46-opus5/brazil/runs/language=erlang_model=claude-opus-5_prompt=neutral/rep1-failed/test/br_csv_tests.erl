%%%-------------------------------------------------------------------
%%% @doc Unit tests for the CSV reader.
%%%-------------------------------------------------------------------
-module(br_csv_tests).

-include_lib("eunit/include/eunit.hrl").

simple_test() ->
    ?assertEqual([[<<"a">>, <<"b">>], [<<"1">>, <<"2">>]],
                 br_csv:parse(<<"a,b\n1,2\n">>)).

no_trailing_newline_test() ->
    ?assertEqual([[<<"a">>, <<"b">>], [<<"1">>, <<"2">>]],
                 br_csv:parse(<<"a,b\n1,2">>)).

crlf_test() ->
    ?assertEqual([[<<"a">>, <<"b">>], [<<"1">>, <<"2">>]],
                 br_csv:parse(<<"a,b\r\n1,2\r\n">>)).

bom_test() ->
    ?assertEqual([[<<"a">>], [<<"1">>]],
                 br_csv:parse(<<239, 187, 191, "a\n1\n">>)).

quoted_fields_test() ->
    ?assertEqual([[<<"Palmeiras-SP">>, <<"SP">>, <<"1">>]],
                 br_csv:parse(<<"\"Palmeiras-SP\",\"SP\",1">>)).

quoted_comma_test() ->
    ?assertEqual([[<<"Boavista, RJ">>, <<"x">>]],
                 br_csv:parse(<<"\"Boavista, RJ\",x">>)).

escaped_quote_test() ->
    ?assertEqual([[<<"say \"hi\"">>, <<"x">>]],
                 br_csv:parse(<<"\"say \"\"hi\"\"\",x">>)).

quoted_newline_test() ->
    ?assertEqual([[<<"two\nlines">>, <<"x">>], [<<"a">>, <<"b">>]],
                 br_csv:parse(<<"\"two\nlines\",x\na,b">>)).

empty_fields_test() ->
    ?assertEqual([[<<>>, <<"b">>, <<>>]], br_csv:parse(<<",b,">>)).

blank_lines_are_skipped_test() ->
    ?assertEqual([[<<"a">>], [<<"b">>]], br_csv:parse(<<"a\n\nb\n">>)).

utf8_is_preserved_test() ->
    [[Name]] = br_csv:parse(<<"\"São Paulo"/utf8, "\"">>),
    ?assertEqual(<<"São Paulo"/utf8>>, Name).

rows_to_maps_test() ->
    Rows = br_csv:parse(<<"home,away\nSantos,Vasco\n">>),
    ?assertEqual([#{<<"home">> => <<"Santos">>, <<"away">> => <<"Vasco">>}],
                 br_csv:rows_to_maps(Rows)).

short_rows_are_padded_test() ->
    Rows = br_csv:parse(<<"a,b,c\n1\n">>),
    ?assertEqual([#{<<"a">> => <<"1">>, <<"b">> => <<>>, <<"c">> => <<>>}],
                 br_csv:rows_to_maps(Rows)).

fold_file_test() ->
    Path = filename:join(temp_dir(), "br_csv_fold_test.csv"),
    ok = file:write_file(Path, <<"team,goals\nSantos,3\nVasco,1\n">>),
    try
        {ok, Total} = br_csv:fold_file(
                        Path,
                        fun(#{<<"goals">> := G}, Acc) -> Acc + binary_to_integer(G) end,
                        0),
        ?assertEqual(4, Total)
    after
        file:delete(Path)
    end.

missing_file_test() ->
    ?assertMatch({error, enoent}, br_csv:parse_file("does-not-exist.csv")).

real_data_file_test() ->
    case br_loader:data_dir() of
        undefined -> ok;   % data not available in this environment
        Dir ->
            Path = filename:join(Dir, "Brasileirao_Matches.csv"),
            {ok, Header, Rows} = br_csv:parse_file(Path),
            ?assertEqual([<<"datetime">>, <<"home_team">>, <<"home_team_state">>,
                          <<"away_team">>, <<"away_team_state">>, <<"home_goal">>,
                          <<"away_goal">>, <<"season">>, <<"round">>], Header),
            ?assertEqual(4180, length(Rows)),
            ?assert(lists:all(fun(R) -> length(R) =:= 9 end, Rows))
    end.

temp_dir() ->
    case os:getenv("TMPDIR") of
        false -> "/tmp";
        Dir -> Dir
    end.
