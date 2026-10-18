-module(books_api_tests).
-include_lib("eunit/include/eunit.hrl").

validation_test()->
    ?assertNot(books_http_handler:nonempty(<<>>)),
    ?assertNot(books_http_handler:nonempty(<<"  ">>)),
    ?assert(books_http_handler:nonempty(<<"Dune">>)).

decode_book_test()->
    ?assertMatch({error,_},books_http_handler:decode_book(<<"{\"title\":\"Missing author\"}">>)),
    ?assertMatch({ok,#{title:=<<"Dune">>,author:=<<"Frank Herbert">>}},books_http_handler:decode_book(<<"{\"title\":\"Dune\",\"author\":\"Frank Herbert\"}">>)).

database_crud_test()->
    Path="/tmp/books_api_test.db", _=file:delete(Path), {ok,P}=books_db:start_link(Path),
    {ok,B}=books_db:create(#{title=><<"Dune">>,author=><<"Frank Herbert">>,year=>1965,isbn=><<"9780441172719">>}),
    I=maps:get(id,B), ?assertMatch({ok,_},books_db:get(I)), ?assertMatch({ok,[_]},books_db:list(<<"Frank Herbert">>)),
    ?assertEqual(ok,books_db:delete(I)), ?assertEqual(not_found,books_db:delete(I)), gen_server:stop(P), file:delete(Path).
