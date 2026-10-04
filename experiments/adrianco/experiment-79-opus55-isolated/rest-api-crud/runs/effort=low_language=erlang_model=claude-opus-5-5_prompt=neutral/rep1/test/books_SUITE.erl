%% Integration tests: boots the application against a temporary SQLite file
%% and exercises the HTTP API with httpc.
-module(books_SUITE).

-include_lib("common_test/include/ct.hrl").
-include_lib("stdlib/include/assert.hrl").

-export([all/0, init_per_suite/1, end_per_suite/1, init_per_testcase/2, end_per_testcase/2]).
-export([health/1, create_and_get/1, create_minimal/1, create_validation/1,
         create_invalid_json/1, list_and_filter/1, update/1, update_errors/1,
         delete/1, not_found/1, method_not_allowed/1, persists_across_restart/1]).

-define(PORT, 18089).

all() ->
    [health, create_and_get, create_minimal, create_validation, create_invalid_json,
     list_and_filter, update, update_errors, delete, not_found, method_not_allowed,
     persists_across_restart].

init_per_suite(Config) ->
    DbPath = filename:join(?config(priv_dir, Config), "test.db"),
    application:load(books),
    application:set_env(books, port, ?PORT),
    application:set_env(books, db_path, DbPath),
    {ok, _} = application:ensure_all_started(inets),
    {ok, _} = application:ensure_all_started(books),
    Config.

end_per_suite(_Config) ->
    application:stop(books),
    ok.

init_per_testcase(_Case, Config) ->
    ok = books_db:delete_all(),
    Config.

end_per_testcase(_Case, _Config) ->
    ok.

%% tests

health(_Config) ->
    {200, Body} = request(get, "/health"),
    ?assertEqual(#{<<"status">> => <<"ok">>}, Body).

create_and_get(_Config) ->
    {201, Created} = request(post, "/books", dune()),
    #{<<"id">> := Id} = Created,
    ?assert(is_integer(Id)),
    ?assertMatch(#{<<"title">> := <<"Dune">>, <<"author">> := <<"Frank Herbert">>,
                   <<"year">> := 1965, <<"isbn">> := <<"9780441172719">>}, Created),
    {200, Fetched} = request(get, "/books/" ++ integer_to_list(Id)),
    ?assertEqual(Created, Fetched).

create_minimal(_Config) ->
    {201, Created} = request(post, "/books", #{title => <<"T">>, author => <<"A">>}),
    ?assertMatch(#{<<"year">> := null, <<"isbn">> := null}, Created).

create_validation(_Config) ->
    {400, NoTitle} = request(post, "/books", #{author => <<"A">>}),
    ?assertMatch(#{<<"details">> := [<<"title is required">>]}, NoTitle),
    {400, _} = request(post, "/books", #{title => <<"T">>}),
    {400, Both} = request(post, "/books", #{title => <<"  ">>, author => <<>>}),
    ?assertEqual(2, length(maps:get(<<"details">>, Both))),
    {400, _} = request(post, "/books", #{title => 1, author => <<"A">>}),
    {400, _} = request(post, "/books", #{title => <<"T">>, author => <<"A">>, year => <<"x">>}),
    {400, _} = request(post, "/books", #{title => <<"T">>, author => <<"A">>, isbn => 5}),
    {400, _} = request(post, "/books", [1, 2]),
    {200, []} = request(get, "/books").

create_invalid_json(_Config) ->
    {400, Body} = raw_request(post, "/books", <<"{not json">>),
    ?assertMatch(#{<<"error">> := _}, Body),
    {400, _} = raw_request(post, "/books", <<>>).

list_and_filter(_Config) ->
    {200, []} = request(get, "/books"),
    {201, _} = request(post, "/books", dune()),
    {201, _} = request(post, "/books", #{title => <<"Emma">>, author => <<"Jane Austen">>}),
    {201, _} = request(post, "/books", #{title => <<"Persuasion">>, author => <<"Jane Austen">>}),
    {200, All} = request(get, "/books"),
    ?assertEqual(3, length(All)),
    {200, Austen} = request(get, "/books?author=Jane%20Austen"),
    ?assertEqual([<<"Emma">>, <<"Persuasion">>], [maps:get(<<"title">>, B) || B <- Austen]),
    {200, []} = request(get, "/books?author=Nobody").

update(_Config) ->
    {201, #{<<"id">> := Id}} = request(post, "/books", dune()),
    Path = "/books/" ++ integer_to_list(Id),
    {200, Updated} = request(put, Path, #{title => <<"Dune Messiah">>,
                                          author => <<"Frank Herbert">>, year => 1969}),
    ?assertMatch(#{<<"id">> := Id, <<"title">> := <<"Dune Messiah">>, <<"year">> := 1969,
                   <<"isbn">> := null}, Updated),
    {200, Updated} = request(get, Path).

update_errors(_Config) ->
    {201, #{<<"id">> := Id} = Created} = request(post, "/books", dune()),
    Path = "/books/" ++ integer_to_list(Id),
    {400, _} = request(put, Path, #{title => <<"No author">>}),
    {200, Created} = request(get, Path),
    {404, _} = request(put, "/books/999999", dune()).

delete(_Config) ->
    {201, #{<<"id">> := Id}} = request(post, "/books", dune()),
    Path = "/books/" ++ integer_to_list(Id),
    {204, no_body} = request(delete, Path),
    {404, _} = request(get, Path),
    {404, _} = request(delete, Path).

not_found(_Config) ->
    {404, Body} = request(get, "/books/12345"),
    ?assertMatch(#{<<"error">> := _}, Body),
    {404, _} = request(get, "/books/abc"),
    {404, _} = request(get, "/books/99999999999999999999999999").

method_not_allowed(_Config) ->
    {405, _} = request(delete, "/books"),
    {405, _} = request(post, "/books/1", dune()).

persists_across_restart(_Config) ->
    {201, #{<<"id">> := Id} = Created} = request(post, "/books", dune()),
    ok = application:stop(books),
    {ok, _} = application:ensure_all_started(books),
    {200, Created} = request(get, "/books/" ++ integer_to_list(Id)).

%% helpers

dune() ->
    #{title => <<"Dune">>, author => <<"Frank Herbert">>, year => 1965,
      isbn => <<"9780441172719">>}.

url(Path) ->
    "http://localhost:" ++ integer_to_list(?PORT) ++ Path.

request(Method, Path) ->
    result(httpc:request(Method, {url(Path), []}, [], [{body_format, binary}])).

request(Method, Path, Term) ->
    raw_request(Method, Path, iolist_to_binary(json:encode(Term))).

raw_request(Method, Path, Body) ->
    result(httpc:request(Method, {url(Path), [], "application/json", Body}, [],
                         [{body_format, binary}])).

result({ok, {{_, Status, _}, _Headers, <<>>}}) ->
    {Status, no_body};
result({ok, {{_, Status, _}, Headers, Body}}) ->
    ?assertEqual("application/json", proplists:get_value("content-type", Headers)),
    {Status, json:decode(Body)}.
