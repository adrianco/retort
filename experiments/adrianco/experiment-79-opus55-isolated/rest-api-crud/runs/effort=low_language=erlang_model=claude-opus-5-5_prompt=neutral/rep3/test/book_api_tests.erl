%% Integration tests: boot the real application on an ephemeral port with a
%% throwaway database file and exercise it over HTTP.
-module(book_api_tests).

-include_lib("eunit/include/eunit.hrl").

book_api_test_() ->
    {setup, fun start/0, fun stop/1,
        {foreach, fun reset/0, [
            fun health/0,
            fun create_and_get/0,
            fun create_requires_title_and_author/0,
            fun create_rejects_bad_types/0,
            fun create_rejects_malformed_json/0,
            fun list_and_filter_by_author/0,
            fun update_book/0,
            fun update_validates_and_404s/0,
            fun delete_book/0,
            fun unknown_and_invalid_ids/0,
            fun method_not_allowed/0,
            fun ids_are_not_reused/0
        ]}}.

validate_test_() ->
    V = fun book_api_books_handler:validate/1,
    [
        ?_assertEqual(
            {ok, #{title => <<"T">>, author => <<"A">>, year => null, isbn => null}},
            V(#{<<"title">> => <<" T ">>, <<"author">> => <<"A">>})
        ),
        ?_assertEqual(
            {error, #{title => <<"is required">>, author => <<"must not be blank">>}},
            V(#{<<"author">> => <<"  ">>})
        ),
        ?_assertEqual(
            {error, #{year => <<"must be an integer">>}},
            V(#{<<"title">> => <<"T">>, <<"author">> => <<"A">>, <<"year">> => <<"1999">>})
        )
    ].

%% --- fixtures --------------------------------------------------------------

start() ->
    DbFile = filename:join(
        os:getenv("TMPDIR", "/tmp"),
        "book_api_test_" ++ integer_to_list(erlang:unique_integer([positive])) ++ ".dets"
    ),
    os:unsetenv("PORT"),
    os:unsetenv("BOOKS_DB"),
    application:load(book_api),
    application:set_env(book_api, port, 0),
    application:set_env(book_api, db_file, DbFile),
    {ok, _} = application:ensure_all_started(book_api),
    {ok, _} = application:ensure_all_started(inets),
    DbFile.

stop(DbFile) ->
    application:stop(book_api),
    file:delete(DbFile).

reset() ->
    book_store:clear().

%% --- tests -----------------------------------------------------------------

health() ->
    ?assertEqual({200, #{<<"status">> => <<"ok">>}}, request(get, "/health")).

create_and_get() ->
    {201, Book} = request(post, "/books", dune()),
    #{<<"id">> := Id} = Book,
    ?assert(is_integer(Id)),
    ?assertEqual(
        (dune())#{<<"id">> => Id},
        Book
    ),
    ?assertEqual({200, Book}, request(get, path(Id))).

create_requires_title_and_author() ->
    {422, #{<<"details">> := D1}} = request(post, "/books", #{<<"year">> => 1965}),
    ?assertEqual([<<"author">>, <<"title">>], lists:sort(maps:keys(D1))),
    {422, #{<<"details">> := D2}} =
        request(post, "/books", #{<<"title">> => <<"Dune">>, <<"author">> => <<"">>}),
    ?assertEqual([<<"author">>], maps:keys(D2)),
    ?assertEqual({200, []}, request(get, "/books")).

create_rejects_bad_types() ->
    {422, #{<<"details">> := D}} =
        request(post, "/books", (dune())#{<<"year">> => <<"x">>, <<"isbn">> => 5}),
    ?assertEqual([<<"isbn">>, <<"year">>], lists:sort(maps:keys(D))).

create_rejects_malformed_json() ->
    ?assertMatch({400, #{<<"error">> := _}}, raw_request(post, "/books", <<"{not json">>)),
    ?assertMatch({400, #{<<"error">> := _}}, raw_request(post, "/books", <<"[1,2]">>)),
    ?assertMatch({400, #{<<"error">> := _}}, raw_request(post, "/books", <<>>)).

list_and_filter_by_author() ->
    ?assertEqual({200, []}, request(get, "/books")),
    {201, B1} = request(post, "/books", dune()),
    {201, B2} = request(post, "/books", #{
        <<"title">> => <<"Neuromancer">>, <<"author">> => <<"William Gibson">>
    }),
    {201, B3} = request(post, "/books", #{
        <<"title">> => <<"Children of Dune">>, <<"author">> => <<"Frank Herbert">>
    }),
    ?assertEqual({200, [B1, B2, B3]}, request(get, "/books")),
    ?assertEqual({200, [B1, B3]}, request(get, "/books?author=Frank%20Herbert")),
    ?assertEqual({200, [B2]}, request(get, "/books?author=William+Gibson")),
    ?assertEqual({200, []}, request(get, "/books?author=Nobody")).

update_book() ->
    {201, #{<<"id">> := Id}} = request(post, "/books", dune()),
    New = #{
        <<"title">> => <<"Dune Messiah">>,
        <<"author">> => <<"Frank Herbert">>,
        <<"year">> => 1969,
        <<"isbn">> => null
    },
    Expected = New#{<<"id">> => Id},
    ?assertEqual({200, Expected}, request(put, path(Id), New)),
    ?assertEqual({200, Expected}, request(get, path(Id))).

update_validates_and_404s() ->
    {201, #{<<"id">> := Id} = Book} = request(post, "/books", dune()),
    ?assertMatch({422, _}, request(put, path(Id), #{<<"title">> => <<"Only title">>})),
    ?assertEqual({200, Book}, request(get, path(Id))),
    ?assertMatch({404, _}, request(put, path(Id + 100), dune())).

delete_book() ->
    {201, #{<<"id">> := Id}} = request(post, "/books", dune()),
    ?assertEqual({204, no_body}, request(delete, path(Id))),
    ?assertMatch({404, _}, request(get, path(Id))),
    ?assertMatch({404, _}, request(delete, path(Id))).

unknown_and_invalid_ids() ->
    ?assertMatch({404, #{<<"error">> := _}}, request(get, "/books/12345")),
    ?assertMatch({400, #{<<"error">> := _}}, request(get, "/books/abc")),
    ?assertMatch({400, #{<<"error">> := _}}, request(get, "/books/0")).

method_not_allowed() ->
    ?assertMatch({405, _}, request(delete, "/books")),
    ?assertMatch({405, _}, request(post, "/health", #{})).

ids_are_not_reused() ->
    {201, #{<<"id">> := Id1}} = request(post, "/books", dune()),
    {204, _} = request(delete, path(Id1)),
    {201, #{<<"id">> := Id2}} = request(post, "/books", dune()),
    ?assert(Id2 > Id1).

%% --- helpers ---------------------------------------------------------------

dune() ->
    #{
        <<"title">> => <<"Dune">>,
        <<"author">> => <<"Frank Herbert">>,
        <<"year">> => 1965,
        <<"isbn">> => <<"9780441172719">>
    }.

path(Id) ->
    "/books/" ++ integer_to_list(Id).

url(Path) ->
    "http://127.0.0.1:" ++ integer_to_list(book_api_app:port()) ++ Path.

request(Method, Path) ->
    result(httpc:request(Method, {url(Path), []}, [], [{body_format, binary}])).

request(Method, Path, Json) ->
    raw_request(Method, Path, iolist_to_binary(json:encode(Json))).

raw_request(Method, Path, Body) ->
    result(
        httpc:request(
            Method, {url(Path), [], "application/json", Body}, [], [{body_format, binary}]
        )
    ).

result({ok, {{_, Status, _}, _Headers, <<>>}}) ->
    {Status, no_body};
result({ok, {{_, Status, _}, Headers, Body}}) ->
    ?assertEqual("application/json", proplists:get_value("content-type", Headers)),
    {Status, json:decode(Body)}.
