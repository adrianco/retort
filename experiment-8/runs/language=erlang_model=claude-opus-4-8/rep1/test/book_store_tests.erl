%%%-------------------------------------------------------------------
%% @doc EUnit tests for the book_store persistence layer.
%%%-------------------------------------------------------------------
-module(book_store_tests).
-include_lib("eunit/include/eunit.hrl").

%% Each test runs against a fresh dets file in a private temp dir so
%% runs are isolated and repeatable.
setup() ->
    File = test_file(),
    catch file:delete(File),
    {ok, Pid} = book_store:start_link(File),
    {Pid, File}.

cleanup({Pid, File}) ->
    gen_server:stop(Pid),
    catch file:delete(File),
    ok.

test_file() ->
    Dir = "_test_data",
    ok = filelib:ensure_dir(filename:join(Dir, "x")),
    filename:join(Dir, "book_store_tests.dets").

store_test_() ->
    {foreach, fun setup/0, fun cleanup/1,
     [
        fun create_and_get/1,
        fun create_requires_title_and_author/1,
        fun list_and_filter_by_author/1,
        fun update_book/1,
        fun update_missing_returns_not_found/1,
        fun delete_book/1
     ]}.

create_and_get(_) ->
    fun() ->
        {ok, Book} = book_store:create(#{
            <<"title">> => <<"Programming Erlang">>,
            <<"author">> => <<"Joe Armstrong">>,
            <<"year">> => 2013,
            <<"isbn">> => <<"978-1937785536">>
        }),
        Id = maps:get(<<"id">>, Book),
        ?assert(is_integer(Id)),
        ?assertEqual(<<"Programming Erlang">>, maps:get(<<"title">>, Book)),
        ?assertEqual({ok, Book}, book_store:get(Id))
    end.

create_requires_title_and_author(_) ->
    fun() ->
        ?assertMatch({error, _},
            book_store:create(#{<<"author">> => <<"Nobody">>})),
        ?assertMatch({error, _},
            book_store:create(#{<<"title">> => <<"Untitled">>})),
        ?assertMatch({error, _},
            book_store:create(#{<<"title">> => <<"">>,
                                <<"author">> => <<"X">>}))
    end.

list_and_filter_by_author(_) ->
    fun() ->
        {ok, _} = book_store:create(#{<<"title">> => <<"A">>,
                                      <<"author">> => <<"Alice">>}),
        {ok, _} = book_store:create(#{<<"title">> => <<"B">>,
                                      <<"author">> => <<"Bob">>}),
        {ok, _} = book_store:create(#{<<"title">> => <<"C">>,
                                      <<"author">> => <<"Alice">>}),
        ?assertEqual(3, length(book_store:list())),
        Alice = book_store:list(<<"Alice">>),
        ?assertEqual(2, length(Alice)),
        ?assert(lists:all(fun(B) ->
            maps:get(<<"author">>, B) =:= <<"Alice">>
        end, Alice))
    end.

update_book(_) ->
    fun() ->
        {ok, Book} = book_store:create(#{<<"title">> => <<"Old">>,
                                         <<"author">> => <<"Auth">>}),
        Id = maps:get(<<"id">>, Book),
        {ok, Updated} = book_store:update(Id, #{<<"title">> => <<"New">>}),
        ?assertEqual(<<"New">>, maps:get(<<"title">>, Updated)),
        ?assertEqual(<<"Auth">>, maps:get(<<"author">>, Updated)),
        ?assertEqual(Id, maps:get(<<"id">>, Updated))
    end.

update_missing_returns_not_found(_) ->
    fun() ->
        ?assertEqual({error, not_found},
            book_store:update(99999, #{<<"title">> => <<"X">>,
                                       <<"author">> => <<"Y">>}))
    end.

delete_book(_) ->
    fun() ->
        {ok, Book} = book_store:create(#{<<"title">> => <<"Doomed">>,
                                         <<"author">> => <<"Auth">>}),
        Id = maps:get(<<"id">>, Book),
        ?assertEqual(ok, book_store:delete(Id)),
        ?assertEqual({error, not_found}, book_store:get(Id)),
        ?assertEqual({error, not_found}, book_store:delete(Id))
    end.
