-module(books_http_tests).
-include_lib("eunit/include/eunit.hrl").

route_test_() ->
    {setup, fun setup/0, fun cleanup/1,
     [fun health_check/0, fun rejects_missing_required_fields/0, fun creates_and_lists_books/0]}.

setup() ->
    File = filename:join("/tmp", "books_api_http_eunit.dets"),
    file:delete(File),
    {ok, _} = books_store:start_link(File),
    File.
cleanup(File) ->
    try books_store:stop() catch _:_ -> ok end,
    file:delete(File), ok.

health_check() ->
    ?assertEqual({200, <<"{\"status\":\"ok\"}">>}, books_http:route(<<"GET">>, <<"/health">>, #{}, <<>>)).

rejects_missing_required_fields() ->
    {400, Body} = books_http:route(<<"POST">>, <<"/books">>, #{}, <<"{\"title\":\"Only title\"}">>),
    ?assertNotEqual(nomatch, binary:match(Body, <<"\"error\"">>)).

creates_and_lists_books() ->
    {201, Created} = books_http:route(<<"POST">>, <<"/books">>, #{}, <<"{\"title\":\"Dune\",\"author\":\"Frank Herbert\",\"year\":1965}">>),
    ?assertNotEqual(nomatch, binary:match(Created, <<"\"id\":1">>)),
    {200, Listed} = books_http:route(<<"GET">>, <<"/books?author=Frank+Herbert">>, #{}, <<>>),
    ?assertEqual($[, binary:first(Listed)),
    ?assertNotEqual(nomatch, binary:match(Listed, <<"Dune">>)).
