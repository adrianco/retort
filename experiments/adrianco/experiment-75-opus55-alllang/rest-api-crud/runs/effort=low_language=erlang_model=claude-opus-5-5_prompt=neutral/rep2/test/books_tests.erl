-module(books_tests).
-include_lib("eunit/include/eunit.hrl").

-define(PORT, 0).
-define(URL(P), "http://localhost:" ++ integer_to_list(books_http:port()) ++ P).

validate_test_() ->
    [?_assertMatch({ok, _}, books_api:validate(#{<<"title">> => <<"T">>, <<"author">> => <<"A">>})),
     ?_assertMatch({error, [_, _]}, books_api:validate(#{})),
     ?_assertMatch({error, [_]}, books_api:validate(#{<<"title">> => <<" ">>, <<"author">> => <<"A">>})),
     ?_assertMatch({error, [_]}, books_api:validate(#{<<"title">> => <<"T">>, <<"author">> => <<"A">>,
                                                      <<"year">> => <<"x">>})),
     ?_assertMatch({error, _}, books_api:validate([1]))].

api_test_() ->
    {setup, fun setup/0, fun cleanup/1,
     [fun health/0, fun crud/0, fun filter/0, fun invalid/0]}.

setup() ->
    File = "test_books.dets",
    file:delete(File),
    application:load(books),
    application:set_env(books, port, ?PORT),
    application:set_env(books, db_file, File),
    {ok, _} = application:ensure_all_started(books),
    {ok, _} = application:ensure_all_started(inets),
    File.

cleanup(File) ->
    application:stop(books),
    file:delete(File).

req(Method, Path) -> decode(httpc:request(Method, {?URL(Path), []}, [], [])).
req(Method, Path, Body) ->
    decode(httpc:request(Method, {?URL(Path), [], "application/json",
                                  iolist_to_binary(json:encode(Body))}, [], [])).
decode({ok, {{_, Code, _}, _, ""}}) -> {Code, none};
decode({ok, {{_, Code, _}, _, Body}}) -> {Code, json:decode(list_to_binary(Body))}.

health() -> ?assertEqual({200, #{<<"status">> => <<"ok">>}}, req(get, "/health")).

crud() ->
    {201, B} = req(post, "/books", #{title => <<"Dune">>, author => <<"Herbert">>,
                                     year => 1965, isbn => <<"978-0441013593">>}),
    Id = integer_to_list(maps:get(<<"id">>, B)),
    ?assertEqual({200, B}, req(get, "/books/" ++ Id)),
    {200, U} = req(put, "/books/" ++ Id, #{title => <<"Dune Messiah">>, author => <<"Herbert">>, year => 1969}),
    ?assertEqual(<<"Dune Messiah">>, maps:get(<<"title">>, U)),
    ?assertEqual({204, none}, req(delete, "/books/" ++ Id)),
    ?assertMatch({404, _}, req(get, "/books/" ++ Id)),
    ?assertMatch({404, _}, req(delete, "/books/" ++ Id)),
    ?assertMatch({404, _}, req(put, "/books/9999", #{title => <<"x">>, author => <<"y">>})).

filter() ->
    {201, _} = req(post, "/books", #{title => <<"Emma">>, author => <<"Jane Austen">>}),
    {201, _} = req(post, "/books", #{title => <<"Ubik">>, author => <<"Dick">>}),
    {200, All} = req(get, "/books"),
    ?assert(length(All) >= 2),
    {200, [Only]} = req(get, "/books?author=Jane%20Austen"),
    ?assertEqual(<<"Emma">>, maps:get(<<"title">>, Only)).

invalid() ->
    ?assertMatch({400, #{<<"details">> := [_]}}, req(post, "/books", #{title => <<"No author">>})),
    ?assertMatch({400, _}, req(post, "/books", <<"not an object">>)),
    ?assertMatch({404, _}, req(get, "/books/abc")).
