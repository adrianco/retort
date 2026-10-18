%% Integration tests: each test starts a real store and HTTP listener on an
%% ephemeral port and talks to it over the network with httpc.
-module(books_api_tests).

-include_lib("eunit/include/eunit.hrl").

api_test_() ->
    {foreach, fun setup/0, fun cleanup/1,
     [fun health_check/1,
      fun unknown_routes_and_bad_ids/1,
      fun create_and_fetch/1,
      fun create_validation/1,
      fun malformed_json/1,
      fun list_with_author_filter/1,
      fun update_book/1,
      fun delete_book/1]}.

setup() ->
    {ok, _} = application:ensure_all_started(inets),
    File = filename:join(os:getenv("TMPDIR", "/tmp"),
                         "books_test_" ++ integer_to_list(erlang:unique_integer([positive])) ++ ".dets"),
    {ok, Store} = books_store:start_link(#{file => File}),
    {ok, Http} = books_http:start_link(0),
    Base = "http://127.0.0.1:" ++ integer_to_list(books_http:port(Http)),
    #{store => Store, http => Http, file => File, base => Base}.

cleanup(#{store := Store, http := Http, file := File}) ->
    gen_server:stop(Http),
    gen_server:stop(Store),
    file:delete(File),
    ok.

health_check(Ctx) ->
    {"GET /health returns 200 with status ok", fun() ->
        {Code, Body} = call(get, Ctx, "/health"),
        ?assertEqual(200, Code),
        ?assertEqual(#{<<"status">> => <<"ok">>}, json:decode(Body))
    end}.

unknown_routes_and_bad_ids(Ctx) ->
    {"unknown routes return 404 and non-integer ids return 400", fun() ->
        ?assertMatch({404, _}, call(get, Ctx, "/nope")),
        ?assertMatch({400, _}, call(get, Ctx, "/books/abc")),
        ?assertMatch({405, _}, call(options, Ctx, "/books/1"))
    end}.

create_and_fetch(Ctx) ->
    {"POST /books creates a book that GET /books/{id} returns", fun() ->
        Book = create_book(Ctx, #{title => <<"Dune">>, author => <<"Frank Herbert">>,
                                  year => 1965, isbn => <<"9780441172719">>}),
        ?assertEqual(<<"Dune">>, maps:get(<<"title">>, Book)),
        ?assertEqual(1965, maps:get(<<"year">>, Book)),
        Id = integer_to_list(maps:get(<<"id">>, Book)),
        ?assertEqual({200, Book}, fetch_decoded(Ctx, "/books/" ++ Id)),
        ?assertMatch({404, _}, call(get, Ctx, "/books/99999"))
    end}.

create_validation(Ctx) ->
    {"POST /books rejects missing or invalid title and author", fun() ->
        Invalid = [#{author => <<"Frank Herbert">>},
                   #{title => <<"   ">>, author => <<"Frank Herbert">>},
                   #{title => <<"Dune">>},
                   #{title => <<"Dune">>, author => <<"">>},
                   #{title => 42, author => <<"Frank Herbert">>},
                   #{title => <<"Dune">>, author => <<"FH">>, year => <<"1965">>}],
        [?assertMatch({400, _}, call(post, Ctx, "/books", json:encode(Body))) || Body <- Invalid],
        ?assertEqual([], list_books(Ctx, ""))
    end}.

malformed_json(Ctx) ->
    {"POST /books rejects malformed or non-object JSON", fun() ->
        ?assertMatch({400, _}, call(post, Ctx, "/books", <<"{not json">>)),
        ?assertMatch({400, _}, call(post, Ctx, "/books", <<"[1,2]">>))
    end}.

list_with_author_filter(Ctx) ->
    {"GET /books lists all books and filters by author", fun() ->
        create_book(Ctx, #{title => <<"Dune">>, author => <<"Frank Herbert">>}),
        create_book(Ctx, #{title => <<"Dune Messiah">>, author => <<"Frank Herbert">>}),
        create_book(Ctx, #{title => <<"Foundation">>, author => <<"Isaac Asimov">>}),
        ?assertEqual([<<"Dune">>, <<"Dune Messiah">>, <<"Foundation">>], titles(list_books(Ctx, ""))),
        ?assertEqual([<<"Dune">>, <<"Dune Messiah">>],
                     titles(list_books(Ctx, "?author=frank%20herbert"))),
        ?assertEqual([], list_books(Ctx, "?author=Nobody"))
    end}.

update_book(Ctx) ->
    {"PUT /books/{id} updates given fields and validates", fun() ->
        Book = create_book(Ctx, #{title => <<"Dune">>, author => <<"Frank Herbert">>}),
        Path = "/books/" ++ integer_to_list(maps:get(<<"id">>, Book)),
        {200, Body} = call(put, Ctx, Path, json:encode(#{year => 1966})),
        Updated = json:decode(Body),
        ?assertEqual(1966, maps:get(<<"year">>, Updated)),
        ?assertEqual(<<"Dune">>, maps:get(<<"title">>, Updated)),
        ?assertMatch({400, _}, call(put, Ctx, Path, json:encode(#{title => <<"">>}))),
        ?assertMatch({404, _}, call(put, Ctx, "/books/99999", json:encode(#{year => 1})))
    end}.

delete_book(Ctx) ->
    {"DELETE /books/{id} removes the book", fun() ->
        Book = create_book(Ctx, #{title => <<"Dune">>, author => <<"Frank Herbert">>}),
        Path = "/books/" ++ integer_to_list(maps:get(<<"id">>, Book)),
        ?assertMatch({204, <<>>}, call(delete, Ctx, Path)),
        ?assertMatch({404, _}, call(get, Ctx, Path)),
        ?assertMatch({404, _}, call(delete, Ctx, Path))
    end}.

%% Helpers

call(Method, Ctx, Path) ->
    Url = maps:get(base, Ctx) ++ Path,
    {ok, {{_, Code, _}, _, Body}} =
        httpc:request(Method, {Url, []}, [], [{body_format, binary}]),
    {Code, Body}.

call(Method, Ctx, Path, Body) when Method =:= post; Method =:= put ->
    Url = maps:get(base, Ctx) ++ Path,
    {ok, {{_, Code, _}, _, RespBody}} =
        httpc:request(Method, {Url, [], "application/json", iolist_to_binary(Body)}, [],
                      [{body_format, binary}]),
    {Code, RespBody};
call(Method, Ctx, Path, _Body) ->
    call(Method, Ctx, Path).

create_book(Ctx, Attrs) ->
    {201, Body} = call(post, Ctx, "/books", json:encode(Attrs)),
    json:decode(Body).

list_books(Ctx, Query) ->
    {200, Body} = call(get, Ctx, "/books" ++ Query),
    json:decode(Body).

fetch_decoded(Ctx, Path) ->
    {Code, Body} = call(get, Ctx, Path),
    {Code, json:decode(Body)}.

titles(Books) ->
    [maps:get(<<"title">>, B) || B <- Books].
