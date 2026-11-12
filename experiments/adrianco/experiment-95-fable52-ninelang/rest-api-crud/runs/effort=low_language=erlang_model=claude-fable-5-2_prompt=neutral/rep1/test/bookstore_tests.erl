-module(bookstore_tests).
-include_lib("eunit/include/eunit.hrl").

%%% fixture: boots the whole application on a random port with an
%%% in-memory SQLite database, and drives it over real HTTP.

api_test_() ->
    {setup, fun start/0, fun stop/1,
     {foreach, fun bookstore_db:clear/0, fun(_) -> ok end, [
        {"health check", fun health/0},
        {"create and fetch", fun create_and_get/0},
        {"optional fields default to null", fun optional_fields/0},
        {"validation errors", fun validation/0},
        {"list and author filter", fun list_and_filter/0},
        {"update", fun update/0},
        {"delete", fun delete/0},
        {"unknown ids give 404", fun not_found/0},
        {"method not allowed", fun method_not_allowed/0}
     ]}}.

start() ->
    application:load(bookstore),
    application:set_env(bookstore, port, 0),
    application:set_env(bookstore, db_path, ":memory:"),
    {ok, _} = application:ensure_all_started(inets),
    {ok, Started} = application:ensure_all_started(bookstore),
    Started.

stop(Started) ->
    [application:stop(A) || A <- lists:reverse(Started)],
    ok.

%%% tests

health() ->
    ?assertMatch({200, #{<<"status">> := <<"ok">>}}, req(get, "/health")).

create_and_get() ->
    {201, Book} = req(post, "/books", dune()),
    #{<<"id">> := Id} = Book,
    ?assert(is_integer(Id)),
    ?assertEqual(<<"Dune">>, maps:get(<<"title">>, Book)),
    ?assertEqual(<<"Frank Herbert">>, maps:get(<<"author">>, Book)),
    ?assertEqual(1965, maps:get(<<"year">>, Book)),
    ?assertEqual(<<"9780441172719">>, maps:get(<<"isbn">>, Book)),
    ?assertEqual({200, Book}, req(get, path(Id))).

optional_fields() ->
    {201, Book} = req(post, "/books", #{title => <<"T">>, author => <<"A">>}),
    ?assertMatch(#{<<"year">> := null, <<"isbn">> := null}, Book).

validation() ->
    ?assertMatch({400, #{<<"details">> := [<<"title is required">>]}},
                 req(post, "/books", #{author => <<"A">>})),
    ?assertMatch({400, #{<<"details">> := [<<"author is required">>]}},
                 req(post, "/books", #{title => <<"T">>, author => <<"  ">>})),
    ?assertMatch({400, #{<<"details">> := [_, _]}}, req(post, "/books", #{})),
    ?assertMatch({400, #{<<"details">> := [<<"year must be an integer">>]}},
                 req(post, "/books", #{title => <<"T">>, author => <<"A">>,
                                       year => <<"1999">>})),
    ?assertMatch({400, _}, req(post, "/books", [1, 2])),
    ?assertMatch({400, #{<<"error">> := <<"invalid JSON body">>}},
                 raw(post, "/books", <<"{not json">>)),
    %% nothing was stored
    ?assertEqual({200, []}, req(get, "/books")),
    %% PUT validates as well
    {201, #{<<"id">> := Id}} = req(post, "/books", dune()),
    ?assertMatch({400, _}, req(put, path(Id), #{title => <<"only title">>})).

list_and_filter() ->
    ?assertEqual({200, []}, req(get, "/books")),
    {201, _} = req(post, "/books", dune()),
    {201, _} = req(post, "/books", #{title => <<"Emma">>, author => <<"Jane Austen">>}),
    {201, _} = req(post, "/books", #{title => <<"Children of Dune">>,
                                     author => <<"Frank Herbert">>}),
    {200, All} = req(get, "/books"),
    ?assertEqual(3, length(All)),
    {200, Herbert} = req(get, "/books?author=Frank%20Herbert"),
    ?assertEqual([<<"Dune">>, <<"Children of Dune">>],
                 [maps:get(<<"title">>, B) || B <- Herbert]),
    ?assertEqual({200, []}, req(get, "/books?author=Nobody")).

update() ->
    {201, #{<<"id">> := Id}} = req(post, "/books", dune()),
    {200, Updated} = req(put, path(Id), #{title => <<"Dune Messiah">>,
                                          author => <<"Frank Herbert">>,
                                          year => 1969}),
    ?assertMatch(#{<<"id">> := Id, <<"title">> := <<"Dune Messiah">>,
                   <<"year">> := 1969, <<"isbn">> := null}, Updated),
    ?assertEqual({200, Updated}, req(get, path(Id))).

delete() ->
    {201, #{<<"id">> := Id}} = req(post, "/books", dune()),
    ?assertEqual({204, no_body}, req(delete, path(Id))),
    ?assertMatch({404, _}, req(get, path(Id))),
    ?assertMatch({404, _}, req(delete, path(Id))).

not_found() ->
    ?assertMatch({404, #{<<"error">> := _}}, req(get, "/books/9999")),
    ?assertMatch({404, _}, req(get, "/books/abc")),
    ?assertMatch({404, _}, req(put, "/books/9999", dune())),
    ?assertMatch({404, _}, req(delete, "/books/9999")).

method_not_allowed() ->
    ?assertMatch({405, _}, req(delete, "/books")),
    ?assertMatch({405, _}, raw(post, "/health", <<"{}">>)).

%%% pure unit tests of validation

validate_test_() ->
    [?_assertEqual({ok, #{title => <<"T">>, author => <<"A">>, year => null, isbn => null}},
                   bookstore_handler:validate(#{<<"title">> => <<"T">>, <<"author">> => <<"A">>})),
     ?_assertMatch({error, [<<"title must be a string">>]},
                   bookstore_handler:validate(#{<<"title">> => 5, <<"author">> => <<"A">>})),
     ?_assertMatch({error, [_]}, bookstore_handler:validate(<<"str">>))].

%%% helpers

dune() ->
    #{title => <<"Dune">>, author => <<"Frank Herbert">>,
      year => 1965, isbn => <<"9780441172719">>}.

path(Id) -> "/books/" ++ integer_to_list(Id).

url(Path) ->
    "http://127.0.0.1:" ++ integer_to_list(bookstore_app:port()) ++ Path.

req(Method, Path) ->
    result(httpc:request(Method, {url(Path), []}, [], [{body_format, binary}])).

req(Method, Path, Body) ->
    raw(Method, Path, iolist_to_binary(json:encode(Body))).

raw(Method, Path, Body) ->
    result(httpc:request(Method, {url(Path), [], "application/json", Body},
                         [], [{body_format, binary}])).

result({ok, {{_, Status, _}, _Headers, <<>>}}) -> {Status, no_body};
result({ok, {{_, Status, _}, _Headers, Body}}) -> {Status, json:decode(Body)}.
