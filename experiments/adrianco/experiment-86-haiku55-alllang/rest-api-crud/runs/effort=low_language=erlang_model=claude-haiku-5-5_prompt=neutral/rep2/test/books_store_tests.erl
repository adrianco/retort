-module(books_store_tests).
-include_lib("eunit/include/eunit.hrl").

-define(DB, "books_store_test.dets").

store_test_() ->
    {foreach, fun setup/0, fun cleanup/1, [
        fun create_assigns_sequential_ids/1,
        fun get_returns_book_or_not_found/1,
        fun list_filters_by_author/1,
        fun update_replaces_book/1,
        fun delete_removes_book/1,
        fun books_survive_restart/1
    ]}.

setup() ->
    file:delete(?DB),
    {ok, _} = books_store:start_link(?DB),
    ok.

cleanup(_) ->
    gen_server:stop(books_store),
    file:delete(?DB),
    ok.

attrs(Title, Author) ->
    #{title => Title, author => Author, year => null, isbn => null}.

create_assigns_sequential_ids(_) ->
    fun() ->
        {ok, #{id := 1, title := <<"A">>}} = books_store:create(attrs(<<"A">>, <<"X">>)),
        {ok, #{id := 2}} = books_store:create(attrs(<<"B">>, <<"X">>))
    end.

get_returns_book_or_not_found(_) ->
    fun() ->
        {ok, #{id := Id}} = books_store:create(attrs(<<"A">>, <<"X">>)),
        ?assertMatch({ok, #{title := <<"A">>}}, books_store:get(Id)),
        ?assertEqual({error, not_found}, books_store:get(Id + 100))
    end.

list_filters_by_author(_) ->
    fun() ->
        {ok, _} = books_store:create(attrs(<<"A">>, <<"Herbert">>)),
        {ok, _} = books_store:create(attrs(<<"B">>, <<"Asimov">>)),
        {ok, _} = books_store:create(attrs(<<"C">>, <<"Herbert">>)),
        {ok, All} = books_store:list(undefined),
        ?assertEqual([<<"A">>, <<"B">>, <<"C">>], [T || #{title := T} <- All]),
        {ok, Herbert} = books_store:list(<<"Herbert">>),
        ?assertEqual([<<"A">>, <<"C">>], [T || #{title := T} <- Herbert]),
        ?assertEqual({ok, []}, books_store:list(<<"Nobody">>))
    end.

update_replaces_book(_) ->
    fun() ->
        {ok, #{id := Id}} = books_store:create(attrs(<<"A">>, <<"X">>)),
        {ok, Updated} = books_store:update(Id, attrs(<<"New">>, <<"Y">>)),
        ?assertEqual(Id, maps:get(id, Updated)),
        ?assertMatch({ok, #{title := <<"New">>, author := <<"Y">>}}, books_store:get(Id)),
        ?assertEqual({error, not_found}, books_store:update(Id + 100, attrs(<<"Z">>, <<"Z">>)))
    end.

delete_removes_book(_) ->
    fun() ->
        {ok, #{id := Id}} = books_store:create(attrs(<<"A">>, <<"X">>)),
        ?assertEqual(ok, books_store:delete(Id)),
        ?assertEqual({error, not_found}, books_store:get(Id)),
        ?assertEqual({error, not_found}, books_store:delete(Id))
    end.

books_survive_restart(_) ->
    fun() ->
        {ok, #{id := Id}} = books_store:create(attrs(<<"Kept">>, <<"X">>)),
        ok = gen_server:stop(books_store),
        {ok, _} = books_store:start_link(?DB),
        ?assertMatch({ok, #{title := <<"Kept">>}}, books_store:get(Id)),
        %% The id counter also persists, so new ids do not collide.
        {ok, #{id := NewId}} = books_store:create(attrs(<<"Next">>, <<"X">>)),
        ?assert(NewId > Id)
    end.
