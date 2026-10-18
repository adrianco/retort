%%% Feature: CSV files with quoting, byte-order marks and mixed line endings load correctly.
-module(bs_csv_tests).

-include_lib("eunit/include/eunit.hrl").

%% Scenario: Quoted fields keep their commas and escaped quotes
quoted_fields_test_() ->
    ?_assertEqual([[<<"a">>, <<"b,c">>, <<"d\"e">>], [<<"f">>, <<"g">>, <<"h">>]],
                  bs_csv:parse(<<"a,\"b,c\",\"d\"\"e\"\nf,g,h\n">>)).

%% Scenario: Windows line endings and blank lines are tolerated
line_endings_test_() ->
    ?_assertEqual([[<<"x">>, <<"y">>], [<<"1">>, <<"2">>]],
                  bs_csv:parse(<<"x,y\r\n\r\n1,2\r\n">>)).

%% Scenario: A UTF-8 byte-order mark does not corrupt the first header
bom_test_() ->
    ?_assertEqual([[<<"ID">>, <<"Name">>]], bs_csv:parse(<<16#EF, 16#BB, 16#BF, "ID,Name">>)).

%% Scenario: Accented text passes through unchanged
utf8_test_() ->
    ?_assertEqual([[unicode:characters_to_binary("São Paulo")]],
                  bs_csv:parse(unicode:characters_to_binary("São Paulo"))).
