%%%-------------------------------------------------------------------
%%% @doc Unit tests for the JSON layer used by the MCP transport.
%%%-------------------------------------------------------------------
-module(br_json_tests).

-include_lib("eunit/include/eunit.hrl").

atom_keys_become_strings_test() ->
    ?assertEqual(<<"{\"team\":\"santos\"}">>, br_json:encode(#{team => <<"santos">>})).

undefined_becomes_null_test() ->
    ?assertEqual(<<"{\"season\":null}">>, br_json:encode(#{season => undefined})),
    ?assertEqual(<<"{\"season\":null}">>, br_json:encode(#{season => null})).

booleans_survive_test() ->
    ?assertEqual(<<"{\"complete\":true}">>, br_json:encode(#{complete => true})),
    ?assertEqual(<<"{\"complete\":false}">>, br_json:encode(#{complete => false})).

empty_list_is_an_array_test() ->
    ?assertEqual(<<"{\"suggestions\":[]}">>, br_json:encode(#{suggestions => []})).

nested_structures_test() ->
    Json = br_json:encode(#{table => [#{position => 1, team => <<"flamengo">>}]}),
    {ok, Decoded} = br_json:decode(Json),
    ?assertEqual(#{<<"table">> => [#{<<"position">> => 1, <<"team">> => <<"flamengo">>}]},
                 Decoded).

utf8_round_trip_test() ->
    Json = br_json:encode(#{name => <<"São Paulo"/utf8>>}),
    {ok, #{<<"name">> := Name}} = br_json:decode(Json),
    ?assertEqual(<<"São Paulo"/utf8>>, Name).

latin1_data_is_repaired_test() ->
    %% "Sao Paulo" with a Latin-1 encoded a-tilde must not break encoding.
    Json = br_json:encode(#{name => <<"S", 227, "o Paulo">>}),
    {ok, #{<<"name">> := Name}} = br_json:decode(Json),
    ?assertEqual(<<"São Paulo"/utf8>>, Name).

decode_error_test() ->
    ?assertMatch({error, _}, br_json:decode(<<"{not json">>)).

float_precision_test() ->
    Json = br_json:encode(#{goals_per_match => 2.47}),
    {ok, #{<<"goals_per_match">> := V}} = br_json:decode(Json),
    ?assert(abs(V - 2.47) < 0.0001).
