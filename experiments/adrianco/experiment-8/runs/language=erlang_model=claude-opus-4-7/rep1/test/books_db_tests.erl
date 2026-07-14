-module(books_db_tests).
-include_lib("eunit/include/eunit.hrl").

-define(TEST_FILE, "books_test.dets").

setup() ->
    file:delete(?TEST_FILE),
    application:set_env(books_app, db_file, ?TEST_FILE),
    ok = books_db:init(),
    ok.

teardown(_) ->
    books_db:close(),
    file:delete(?TEST_FILE),
    ok.

db_test_() ->
    {foreach, fun setup/0, fun teardown/1, [
        fun create_returns_book_with_id/0,
        fun get_returns_existing_book/0,
        fun get_missing_returns_not_found/0,
        fun list_returns_all_books/0,
        fun list_by_author_filters_results/0,
        fun update_modifies_existing_book/0,
        fun update_missing_returns_not_found/0,
        fun delete_removes_book/0,
        fun delete_missing_returns_not_found/0
    ]}.

create_returns_book_with_id() ->
    {ok, Book} = books_db:create(#{
        <<"title">> => <<"Erlang in Anger">>,
        <<"author">> => <<"Fred Hebert">>,
        <<"year">> => 2014,
        <<"isbn">> => <<"978-1-329-12164-3">>
    }),
    ?assert(maps:is_key(<<"id">>, Book)),
    ?assertEqual(<<"Erlang in Anger">>, maps:get(<<"title">>, Book)).

get_returns_existing_book() ->
    {ok, Created} = books_db:create(#{
        <<"title">> => <<"Programming Erlang">>,
        <<"author">> => <<"Joe Armstrong">>
    }),
    Id = maps:get(<<"id">>, Created),
    {ok, Fetched} = books_db:get(Id),
    ?assertEqual(Created, Fetched).

get_missing_returns_not_found() ->
    ?assertEqual({error, not_found}, books_db:get(<<"deadbeef">>)).

list_returns_all_books() ->
    {ok, []} = books_db:list(),
    {ok, _} = books_db:create(#{<<"title">> => <<"A">>, <<"author">> => <<"X">>}),
    {ok, _} = books_db:create(#{<<"title">> => <<"B">>, <<"author">> => <<"Y">>}),
    {ok, Books} = books_db:list(),
    ?assertEqual(2, length(Books)).

list_by_author_filters_results() ->
    {ok, _} = books_db:create(#{<<"title">> => <<"A">>, <<"author">> => <<"Joe">>}),
    {ok, _} = books_db:create(#{<<"title">> => <<"B">>, <<"author">> => <<"Joe">>}),
    {ok, _} = books_db:create(#{<<"title">> => <<"C">>, <<"author">> => <<"Robert">>}),
    {ok, Joes} = books_db:list_by_author(<<"Joe">>),
    ?assertEqual(2, length(Joes)),
    {ok, Roberts} = books_db:list_by_author(<<"Robert">>),
    ?assertEqual(1, length(Roberts)),
    {ok, None} = books_db:list_by_author(<<"Nobody">>),
    ?assertEqual([], None).

update_modifies_existing_book() ->
    {ok, Created} = books_db:create(#{
        <<"title">> => <<"Old Title">>,
        <<"author">> => <<"Joe">>
    }),
    Id = maps:get(<<"id">>, Created),
    {ok, Updated} = books_db:update(Id, #{<<"title">> => <<"New Title">>}),
    ?assertEqual(<<"New Title">>, maps:get(<<"title">>, Updated)),
    ?assertEqual(<<"Joe">>, maps:get(<<"author">>, Updated)),
    ?assertEqual(Id, maps:get(<<"id">>, Updated)).

update_missing_returns_not_found() ->
    ?assertEqual({error, not_found},
        books_db:update(<<"nosuchid">>, #{<<"title">> => <<"X">>})).

delete_removes_book() ->
    {ok, Created} = books_db:create(#{<<"title">> => <<"T">>, <<"author">> => <<"A">>}),
    Id = maps:get(<<"id">>, Created),
    ?assertEqual(ok, books_db:delete(Id)),
    ?assertEqual({error, not_found}, books_db:get(Id)).

delete_missing_returns_not_found() ->
    ?assertEqual({error, not_found}, books_db:delete(<<"missing">>)).
