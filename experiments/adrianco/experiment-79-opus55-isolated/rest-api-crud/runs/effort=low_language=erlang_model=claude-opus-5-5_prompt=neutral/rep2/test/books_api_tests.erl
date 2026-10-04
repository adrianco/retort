%% Integration tests: boot the application against an in-memory SQLite
%% database and exercise the HTTP API with httpc.
-module(books_api_tests).

-include_lib("eunit/include/eunit.hrl").

-define(PORT, 18089).

api_test_() ->
    {setup, fun start/0, fun stop/1,
        {foreach, fun() -> books_db:delete_all() end, [
            fun health/0,
            fun create_and_get/0,
            fun create_requires_title_and_author/0,
            fun create_rejects_bad_input/0,
            fun list_and_filter_by_author/0,
            fun update_book/0,
            fun delete_book/0,
            fun unknown_and_invalid_ids/0,
            fun method_not_allowed/0
        ]}}.

validate_test_() ->
    [
        ?_assertEqual(
            {ok, #{title => <<"T">>, author => <<"A">>, year => null, isbn => null}},
            books_handler:validate(#{<<"title">> => <<" T ">>, <<"author">> => <<"A">>})
        ),
        ?_assertEqual(
            {error, #{title => <<"is required">>, author => <<"must be a string">>}},
            books_handler:validate(#{<<"title">> => <<"  ">>, <<"author">> => 1})
        ),
        ?_assertMatch({error, #{body := _}}, books_handler:validate([1, 2]))
    ].

start() ->
    {ok, _} = application:ensure_all_started(inets),
    application:load(books),
    application:set_env(books, port, ?PORT),
    application:set_env(books, db_path, ":memory:"),
    os:unsetenv("PORT"),
    {ok, _} = application:ensure_all_started(books),
    ok.

stop(_) ->
    application:stop(books).

health() ->
    ?assertEqual({200, #{<<"status">> => <<"ok">>}}, req(get, "/health")).

create_and_get() ->
    {201, Created} = req(post, "/books", dune()),
    #{<<"id">> := Id} = Created,
    ?assert(is_integer(Id)),
    ?assertEqual(dune(), maps:remove(<<"id">>, Created)),
    ?assertEqual({200, Created}, req(get, path(Id))).

create_requires_title_and_author() ->
    {422, #{<<"details">> := Details}} = req(post, "/books", #{<<"year">> => 1999}),
    ?assertEqual([<<"author">>, <<"title">>], lists:sort(maps:keys(Details))),
    {422, #{<<"details">> := D2}} =
        req(post, "/books", #{<<"title">> => <<"">>, <<"author">> => <<"A">>}),
    ?assertEqual([<<"title">>], maps:keys(D2)),
    ?assertEqual({200, []}, req(get, "/books")).

create_rejects_bad_input() ->
    ?assertMatch({400, #{<<"error">> := _}}, raw(post, "/books", "{not json")),
    ?assertMatch(
        {422, #{<<"details">> := #{<<"year">> := _}}},
        req(post, "/books", (dune())#{<<"year">> => <<"abc">>})
    ).

list_and_filter_by_author() ->
    {201, A} = req(post, "/books", dune()),
    {201, B} = req(post, "/books", #{<<"title">> => <<"Emma">>, <<"author">> => <<"Jane Austen">>}),
    ?assertEqual(null, maps:get(<<"year">>, B)),
    ?assertEqual({200, [A, B]}, req(get, "/books")),
    ?assertEqual({200, [B]}, req(get, "/books?author=Jane%20Austen")),
    ?assertEqual({200, []}, req(get, "/books?author=Nobody")).

update_book() ->
    {201, #{<<"id">> := Id}} = req(post, "/books", dune()),
    New = #{
        <<"title">> => <<"Dune Messiah">>,
        <<"author">> => <<"Frank Herbert">>,
        <<"year">> => 1969,
        <<"isbn">> => null
    },
    ?assertEqual({200, New#{<<"id">> => Id}}, req(put, path(Id), New)),
    ?assertEqual({200, New#{<<"id">> => Id}}, req(get, path(Id))),
    ?assertMatch({422, _}, req(put, path(Id), #{<<"title">> => <<"x">>})),
    ?assertMatch({404, _}, req(put, "/books/999999", New)).

delete_book() ->
    {201, #{<<"id">> := Id}} = req(post, "/books", dune()),
    ?assertEqual({204, no_body}, req(delete, path(Id))),
    ?assertMatch({404, _}, req(get, path(Id))),
    ?assertMatch({404, _}, req(delete, path(Id))).

unknown_and_invalid_ids() ->
    ?assertMatch({404, #{<<"error">> := _}}, req(get, "/books/12345")),
    ?assertMatch({400, #{<<"error">> := _}}, req(get, "/books/abc")).

method_not_allowed() ->
    ?assertMatch({405, _}, req(delete, "/books")).

dune() ->
    #{
        <<"title">> => <<"Dune">>,
        <<"author">> => <<"Frank Herbert">>,
        <<"year">> => 1965,
        <<"isbn">> => <<"9780441172719">>
    }.

path(Id) ->
    "/books/" ++ integer_to_list(Id).

req(Method, Path) ->
    result(httpc:request(Method, {url(Path), []}, [], [{body_format, binary}])).

req(Method, Path, Body) ->
    raw(Method, Path, json:encode(Body)).

raw(Method, Path, Body) ->
    result(
        httpc:request(
            Method,
            {url(Path), [], "application/json", iolist_to_binary(Body)},
            [],
            [{body_format, binary}]
        )
    ).

url(Path) ->
    "http://localhost:" ++ integer_to_list(?PORT) ++ Path.

result({ok, {{_, Status, _}, _Headers, <<>>}}) ->
    {Status, no_body};
result({ok, {{_, Status, _}, _Headers, Body}}) ->
    {Status, json:decode(Body)}.
