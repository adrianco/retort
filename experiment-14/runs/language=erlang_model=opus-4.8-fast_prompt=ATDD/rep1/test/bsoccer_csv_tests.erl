%%% ===================================================================
%%% Brazilian Soccer MCP Server - CSV reader unit tests
%%%
%%% Context: Finer-grained TDD for `bsoccer_csv', covering the quirks of
%%% the real datasets (quoted commas, escaped quotes, BOM, CRLF) that
%%% the acceptance tests rely on being parsed correctly.
%%% ===================================================================
-module(bsoccer_csv_tests).
-include_lib("eunit/include/eunit.hrl").

simple_rows_test() ->
    Bin = <<"a,b,c\n1,2,3\n4,5,6\n">>,
    {Cols, Rows} = bsoccer_csv:rows_as_maps(bsoccer_csv:parse_binary(Bin)),
    ?assertEqual([<<"a">>, <<"b">>, <<"c">>], Cols),
    ?assertEqual(2, length(Rows)),
    ?assertEqual(<<"2">>, maps:get(<<"b">>, hd(Rows))).

quoted_comma_test() ->
    %% A quoted field containing a comma must stay a single field.
    Bin = <<"name,joined\n\"Messi\",\"Jul 1, 2004\"\n">>,
    {_, [Row]} = bsoccer_csv:rows_as_maps(bsoccer_csv:parse_binary(Bin)),
    ?assertEqual(<<"Jul 1, 2004">>, maps:get(<<"joined">>, Row)).

escaped_quote_test() ->
    Bin = <<"x\n\"a \"\"b\"\" c\"\n">>,
    [_Header, [Field]] = bsoccer_csv:parse_binary(Bin),
    ?assertEqual(<<"a \"b\" c">>, Field).

bom_is_stripped_test() ->
    Bin = <<239, 187, 191, "h1,h2\nv1,v2\n">>,
    {Cols, _} = bsoccer_csv:rows_as_maps(bsoccer_csv:parse_binary(Bin)),
    ?assertEqual(<<"h1">>, hd(Cols)).

crlf_test() ->
    Bin = <<"a,b\r\n1,2\r\n">>,
    {_, [Row]} = bsoccer_csv:rows_as_maps(bsoccer_csv:parse_binary(Bin)),
    ?assertEqual(<<"1">>, maps:get(<<"a">>, Row)).

utf8_preserved_test() ->
    Bin = unicode:characters_to_binary("team\nSão Paulo\n", utf8),
    {_, [Row]} = bsoccer_csv:rows_as_maps(bsoccer_csv:parse_binary(Bin)),
    ?assertEqual(unicode:characters_to_binary("São Paulo", utf8),
                 maps:get(<<"team">>, Row)).
