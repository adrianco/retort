-module(bsmcp_csv_tests).
-include_lib("eunit/include/eunit.hrl").

simple_row_test() ->
    ?assertEqual([[<<"a">>, <<"b">>, <<"c">>]],
                 bsmcp_csv:parse(<<"a,b,c">>)).

multiple_rows_test() ->
    ?assertEqual([[<<"a">>, <<"b">>], [<<"c">>, <<"d">>]],
                 bsmcp_csv:parse(<<"a,b\nc,d">>)).

trailing_newline_test() ->
    ?assertEqual([[<<"a">>, <<"b">>]],
                 bsmcp_csv:parse(<<"a,b\n">>)).

crlf_line_endings_test() ->
    ?assertEqual([[<<"a">>, <<"b">>], [<<"c">>, <<"d">>]],
                 bsmcp_csv:parse(<<"a,b\r\nc,d\r\n">>)).

quoted_field_test() ->
    ?assertEqual([[<<"a">>, <<"b,c">>, <<"d">>]],
                 bsmcp_csv:parse(<<"a,\"b,c\",d">>)).

quoted_field_with_escaped_quote_test() ->
    ?assertEqual([[<<"she said \"hi\"">>]],
                 bsmcp_csv:parse(<<"\"she said \"\"hi\"\"\"">>)).

quoted_field_with_newline_test() ->
    ?assertEqual([[<<"a">>, <<"line1\nline2">>]],
                 bsmcp_csv:parse(<<"a,\"line1\nline2\"">>)).

empty_fields_test() ->
    ?assertEqual([[<<"a">>, <<>>, <<"c">>]],
                 bsmcp_csv:parse(<<"a,,c">>)).

utf8_preserved_test() ->
    %% "São Paulo" and "Grêmio" must be preserved byte-for-byte as UTF-8
    Bin = unicode:characters_to_binary("São Paulo,Grêmio"),
    [[A, B]] = bsmcp_csv:parse(Bin),
    ?assertEqual(unicode:characters_to_binary("São Paulo"), A),
    ?assertEqual(unicode:characters_to_binary("Grêmio"), B).

parse_to_maps_test() ->
    Bin = <<"name,age\nAlice,30\nBob,25">>,
    ?assertEqual([#{<<"name">> => <<"Alice">>, <<"age">> => <<"30">>},
                  #{<<"name">> => <<"Bob">>, <<"age">> => <<"25">>}],
                 bsmcp_csv:parse_to_maps(Bin)).

bom_stripped_in_header_test() ->
    %% A UTF-8 BOM at the start of the file must not corrupt the first header
    Bin = <<239,187,191, "name,age\nAlice,30">>,
    [Row] = bsmcp_csv:parse_to_maps(Bin),
    ?assertEqual(<<"Alice">>, maps:get(<<"name">>, Row)).
