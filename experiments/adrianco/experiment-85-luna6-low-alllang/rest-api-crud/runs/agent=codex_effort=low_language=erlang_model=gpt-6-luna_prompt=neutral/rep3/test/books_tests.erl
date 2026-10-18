-module(books_tests).
-include_lib("eunit/include/eunit.hrl").

json_roundtrip_test() ->
    Input = #{<<"title">> => <<"The \\\"Sea\\\"">>, <<"author">> => <<"A. Writer">>, <<"year">> => 2024},
    {ok, Output} = books_json:decode(books_json:encode(Input)),
    ?assertEqual(Input, Output).

required_fields_validation_test() ->
    ?assertMatch({400, _}, books_http:request(<<"POST">>, <<"/books">>, #{}, <<"{\"title\":\"Only title\"}">>)),
    ok.

crud_and_author_filter_test() ->
    Db = <<"/tmp/books-crud-test.sqlite3">>,
    _ = file:delete(Db),
    {ok, Pid} = books_store:start_link(Db),
    Body1 = <<"{\"title\":\"Book One\",\"author\":\"Alice\",\"year\":2020,\"isbn\":\"111\"}">>,
    {201, Book1} = books_http:request(<<"POST">>, <<"/books">>, #{}, Body1),
    Id = integer_to_binary(maps:get(<<"id">>, Book1)),
    {200, [Book1]} = books_http:request(<<"GET">>, <<"/books?author=Alice">>, #{}, <<>>),
    {200, Book1} = books_http:request(<<"GET">>, <<"/books/", Id/binary>>, #{}, <<>>),
    Body2 = <<"{\"title\":\"Updated\",\"author\":\"Alice\"}">>,
    {200, Updated} = books_http:request(<<"PUT">>, <<"/books/", Id/binary>>, #{}, Body2),
    ?assertEqual(<<"Updated">>, maps:get(<<"title">>, Updated)),
    {204, <<>>} = books_http:request(<<"DELETE">>, <<"/books/", Id/binary>>, #{}, <<>>),
    ?assertMatch({404, _}, books_http:request(<<"GET">>, <<"/books/", Id/binary>>, #{}, <<>>)),
    gen_server:stop(Pid).

health_check_test() ->
    ?assertEqual({200, #{status => <<"ok">>}}, books_http:request(<<"GET">>, <<"/health">>, #{}, <<>>)).
