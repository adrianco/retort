-module(books_tests).
-include_lib("eunit/include/eunit.hrl").

-define(URL(P), "http://127.0.0.1:" ++ integer_to_list(books_http:port()) ++ P).

validate_test_() ->
    [?_assertMatch({ok, #{<<"title">> := <<"T">>}},
                   books_api:validate(#{<<"title">> => <<"T">>, <<"author">> => <<"A">>})),
     ?_assertMatch({error, [_, _]}, books_api:validate(#{})),
     ?_assertMatch({error, [<<"year must be an integer">>]},
                   books_api:validate(#{<<"title">> => <<"T">>, <<"author">> => <<"A">>,
                                        <<"year">> => <<"x">>})),
     ?_assertMatch({error, _}, books_api:validate([1]))].

api_test_() ->
    {setup, fun setup/0, fun cleanup/1,
     [fun health/0, fun crud/0, fun filter/0, fun validation/0, fun not_found/0]}.

setup() ->
    File = "test_books_" ++ integer_to_list(erlang:unique_integer([positive])) ++ ".dets",
    application:load(books),
    application:set_env(books, port, 0),
    application:set_env(books, db_file, File),
    {ok, _} = application:ensure_all_started(books),
    {ok, _} = application:ensure_all_started(inets),
    File.

cleanup(File) ->
    application:stop(books),
    file:delete(File).

req(Method, Path) -> req(Method, Path, undefined).
req(Method, Path, Body) ->
    R = case Body of
            undefined -> {?URL(Path), []};
            _ -> {?URL(Path), [], "application/json", iolist_to_binary(json:encode(Body))}
        end,
    {ok, {{_, Status, _}, _, RespBody}} =
        httpc:request(Method, R, [], [{body_format, binary}]),
    {Status, case RespBody of <<>> -> <<>>; _ -> json:decode(RespBody) end}.

health() ->
    ?assertEqual({200, #{<<"status">> => <<"ok">>}}, req(get, "/health")).

crud() ->
    {201, B} = req(post, "/books", #{title => <<"Dune">>, author => <<"Herbert">>,
                                     year => 1965, isbn => <<"978-0441013593">>}),
    Id = maps:get(<<"id">>, B),
    P = "/books/" ++ integer_to_list(Id),
    ?assertMatch({200, #{<<"title">> := <<"Dune">>, <<"year">> := 1965}}, req(get, P)),
    ?assertMatch({200, #{<<"title">> := <<"Dune Messiah">>, <<"id">> := Id}},
                 req(put, P, #{title => <<"Dune Messiah">>, author => <<"Herbert">>})),
    ?assertMatch({400, _}, req(put, P, #{title => <<"x">>})),
    ?assertEqual({204, <<>>}, req(delete, P)),
    ?assertMatch({404, _}, req(get, P)),
    ?assertMatch({404, _}, req(delete, P)).

filter() ->
    {201, _} = req(post, "/books", #{title => <<"Emma">>, author => <<"Jane Austen">>}),
    {201, _} = req(post, "/books", #{title => <<"Persuasion">>, author => <<"Jane Austen">>}),
    {201, _} = req(post, "/books", #{title => <<"Ubik">>, author => <<"Dick">>}),
    {200, Austen} = req(get, "/books?author=Jane%20Austen"),
    ?assertEqual([<<"Emma">>, <<"Persuasion">>], [maps:get(<<"title">>, X) || X <- Austen]),
    {200, All} = req(get, "/books"),
    ?assert(length(All) >= 3).

validation() ->
    {400, E} = req(post, "/books", #{year => 2000}),
    ?assertEqual([<<"title is required">>, <<"author is required">>],
                 maps:get(<<"details">>, E)),
    ?assertMatch({400, _}, req(post, "/books", #{title => <<"  ">>, author => <<"A">>})).

not_found() ->
    ?assertMatch({404, _}, req(get, "/books/99999")),
    ?assertMatch({404, _}, req(get, "/books/abc")),
    ?assertMatch({404, _}, req(get, "/nope")).
