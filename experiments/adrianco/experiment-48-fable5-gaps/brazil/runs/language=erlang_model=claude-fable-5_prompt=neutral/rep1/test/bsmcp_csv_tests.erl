-module(bsmcp_csv_tests).
-include_lib("eunit/include/eunit.hrl").

simple_test() ->
    ?assertEqual([[<<"a">>, <<"b">>, <<"c">>], [<<"1">>, <<"2">>, <<"3">>]],
                 bsmcp_csv:parse_binary(<<"a,b,c\n1,2,3\n">>)).

no_trailing_newline_test() ->
    ?assertEqual([[<<"a">>, <<"b">>]], bsmcp_csv:parse_binary(<<"a,b">>)).

crlf_test() ->
    ?assertEqual([[<<"a">>], [<<"b">>]], bsmcp_csv:parse_binary(<<"a\r\nb\r\n">>)).

quoted_field_with_comma_test() ->
    ?assertEqual([[<<"a,b">>, <<"c">>]],
                 bsmcp_csv:parse_binary(<<"\"a,b\",c\n">>)).

escaped_quote_test() ->
    ?assertEqual([[<<"say \"hi\"">>]],
                 bsmcp_csv:parse_binary(<<"\"say \"\"hi\"\"\"\n">>)).

quoted_newline_test() ->
    ?assertEqual([[<<"a\nb">>, <<"c">>]],
                 bsmcp_csv:parse_binary(<<"\"a\nb\",c\n">>)).

empty_fields_test() ->
    ?assertEqual([[<<"a">>, <<>>, <<"c">>], [<<>>, <<>>, <<>>]],
                 bsmcp_csv:parse_binary(<<"a,,c\n,,\n">>)).

bom_stripped_test() ->
    ?assertEqual([[<<"a">>, <<"b">>]],
                 bsmcp_csv:parse_binary(<<16#EF, 16#BB, 16#BF, "a,b\n">>)).

utf8_passthrough_test() ->
    [[Field]] = bsmcp_csv:parse_binary(<<"São Paulo"/utf8, "\n">>),
    ?assertEqual(<<"São Paulo"/utf8>>, Field).

blank_lines_skipped_test() ->
    ?assertEqual([[<<"a">>]], bsmcp_csv:parse_binary(<<"a\n\n\n">>)).
