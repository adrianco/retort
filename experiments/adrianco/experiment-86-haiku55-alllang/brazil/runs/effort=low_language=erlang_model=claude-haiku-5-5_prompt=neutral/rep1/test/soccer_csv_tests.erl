%% Feature: CSV parsing of the Kaggle files
-module(soccer_csv_tests).
-include_lib("eunit/include/eunit.hrl").

%% Scenario: quoted fields with commas and escaped quotes
%%   Given a CSV row with a quoted field containing a comma and a doubled quote
%%   When it is parsed
%%   Then the field value keeps the comma and a single quote
quoted_fields_test() ->
    ?assertEqual([[<<"a">>, <<"x, y">>, <<"say \"hi\"">>]],
                 soccer_csv:parse(<<"a,\"x, y\",\"say \"\"hi\"\"\"\n">>)).

%% Scenario: UTF-8 BOM and CRLF line endings
%%   Given a file that starts with a BOM and uses CRLF
%%   When it is parsed into maps
%%   Then the first header name is clean and the values are intact
bom_and_crlf_test() ->
    Csv = <<16#EF, 16#BB, 16#BF, "Name,Club\r\nSão Paulo,\"Grêmio\"\r\n"/utf8>>,
    ?assertEqual([#{<<"Name">> => <<"São Paulo"/utf8>>, <<"Club">> => <<"Grêmio"/utf8>>}],
                 soccer_csv:parse_maps(Csv)).

%% Scenario: quoted field spanning lines
%%   Given a quoted field containing a newline
%%   When it is parsed
%%   Then the newline is kept inside the field
multiline_field_test() ->
    ?assertEqual([[<<"a">>, <<"line1\nline2">>]], soccer_csv:parse(<<"a,\"line1\nline2\"\n">>)).

%% Scenario: short rows are padded to the header width
%%   Given a row with fewer fields than the header
%%   When it is parsed into maps
%%   Then missing fields are empty binaries
short_rows_padded_test() ->
    ?assertEqual([#{<<"a">> => <<"1">>, <<"b">> => <<>>}], soccer_csv:parse_maps(<<"a,b\n1\n">>)).
