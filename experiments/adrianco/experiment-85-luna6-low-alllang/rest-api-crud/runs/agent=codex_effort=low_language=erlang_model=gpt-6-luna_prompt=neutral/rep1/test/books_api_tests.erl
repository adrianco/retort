-module(books_api_tests).
-include_lib("eunit/include/eunit.hrl").

validation_test() ->
    ?assertEqual(ok, books_api_handler:validate(#{<<"title">> => <<"Dune">>, <<"author">> => <<"Frank Herbert">>})),
    ?assertMatch({error, _}, books_api_handler:validate(#{<<"title">> => <<"Dune">>})).

store_crud_test() ->
    Db = "/tmp/books_api_test.db",
    file:delete(Db),
    application:set_env(books_api, database, Db),
    {ok, _} = books_api_store:start_link(),
    Book = #{<<"title">> => <<"Dune">>, <<"author">> => <<"Frank Herbert">>, <<"year">> => 1965, <<"isbn">> => <<"123">>},
    Created = books_api_store:create(Book),
    ?assert(is_map(Created)),
    ?assertEqual(1, maps:get(<<"id">>, Created)),
    ?assertEqual(1, length(books_api_store:list(undefined))),
    ?assertEqual(1, length(books_api_store:list(<<"Frank Herbert">>))),
     ?assertEqual(Created, books_api_store:get(1)),
    Updated = Book#{<<"title">> => <<"Dune Messiah">>},
    ?assertEqual(<<"Dune Messiah">>, maps:get(<<"title">>, books_api_store:update(1, Updated))),
    ?assertEqual([#{<<"changes">> => 1}], books_api_store:delete(1)),
    ok = books_api_store:stop(),
    file:delete(Db).

unknown_book_test() ->
    Db = "/tmp/books_api_empty_test.db",
    file:delete(Db),
    application:set_env(books_api, database, Db),
    case books_api_store:start_link() of {ok, _} -> ok; {error, {already_started, _}} -> ok end,
    ?assertEqual(not_found, books_api_store:get(999)),
    ?assertEqual([#{<<"changes">> => 0}], books_api_store:delete(999)),
    ok = books_api_store:stop(),
    file:delete(Db).
