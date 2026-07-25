%%%-------------------------------------------------------------------
%%% @doc Integration tests for the Mnesia-backed store: CRUD semantics,
%%% the author filter and on-disk durability.
%%% @end
%%%-------------------------------------------------------------------
-module(book_store_tests).

-include_lib("eunit/include/eunit.hrl").
-include("book_api.hrl").

store_test_() ->
    {setup,
     fun() -> Dir = book_api_test_helper:fresh_db_dir(?MODULE),
              ok = book_store:init(Dir),
              Dir
     end,
     fun(_Dir) -> book_store:stop() end,
     {inorder,
      [{foreach,
        fun book_api_test_helper:reset_db/0,
        fun(_) -> ok end,
        [fun create_assigns_sequential_ids/0,
         fun create_stamps_timestamps/0,
         fun get_returns_the_stored_book/0,
         fun get_missing_returns_not_found/0,
         fun list_is_ordered_by_id/0,
         fun list_by_author_is_case_insensitive/0,
         fun list_by_author_can_be_empty/0,
         fun update_replaces_fields_and_keeps_identity/0,
         fun update_missing_returns_not_found/0,
         fun delete_removes_the_book/0,
         fun delete_is_not_idempotent_by_design/0,
         fun count_tracks_the_table_size/0]}]}}.

%%%===================================================================
%%% Create / read
%%%===================================================================

create_assigns_sequential_ids() ->
    {ok, #book{id = Id1}} = book_store:create(attrs(<<"A">>, <<"X">>)),
    {ok, #book{id = Id2}} = book_store:create(attrs(<<"B">>, <<"Y">>)),
    ?assertEqual(1, Id1),
    ?assertEqual(2, Id2).

create_stamps_timestamps() ->
    Before = erlang:system_time(second),
    {ok, Book} = book_store:create(attrs(<<"A">>, <<"X">>)),
    ?assert(Book#book.created_at >= Before),
    ?assertEqual(Book#book.created_at, Book#book.updated_at).

get_returns_the_stored_book() ->
    Attrs = #{title => <<"Dune">>, author => <<"Frank Herbert">>,
              year => 1965, isbn => <<"9780441013593">>},
    {ok, Created} = book_store:create(Attrs),
    ?assertEqual({ok, Created}, book_store:get(Created#book.id)),
    ?assertMatch(#book{title = <<"Dune">>, year = 1965,
                       isbn = <<"9780441013593">>}, Created).

get_missing_returns_not_found() ->
    ?assertEqual({error, not_found}, book_store:get(4242)).

%%%===================================================================
%%% Listing
%%%===================================================================

list_is_ordered_by_id() ->
    Titles = [<<"One">>, <<"Two">>, <<"Three">>],
    [book_store:create(attrs(T, <<"Anon">>)) || T <- Titles],
    ?assertEqual(Titles, [B#book.title || B <- book_store:list()]).

list_by_author_is_case_insensitive() ->
    {ok, _} = book_store:create(attrs(<<"Left Hand">>, <<"Ursula K. Le Guin">>)),
    {ok, _} = book_store:create(attrs(<<"Dune">>, <<"Frank Herbert">>)),
    {ok, _} = book_store:create(attrs(<<"Dispossessed">>, <<"ursula k. le guin">>)),
    Found = book_store:list_by_author(<<"URSULA K. LE GUIN">>),
    ?assertEqual([<<"Left Hand">>, <<"Dispossessed">>],
                 [B#book.title || B <- Found]).

list_by_author_can_be_empty() ->
    {ok, _} = book_store:create(attrs(<<"Dune">>, <<"Frank Herbert">>)),
    ?assertEqual([], book_store:list_by_author(<<"Nobody">>)).

%%%===================================================================
%%% Update / delete
%%%===================================================================

update_replaces_fields_and_keeps_identity() ->
    {ok, Created} = book_store:create(#{title => <<"Old">>, author => <<"A">>,
                                        year => 1900, isbn => <<"9780306406157">>}),
    New = #{title => <<"New">>, author => <<"B">>, year => null, isbn => null},
    {ok, Updated} = book_store:update(Created#book.id, New),
    ?assertEqual(Created#book.id, Updated#book.id),
    ?assertEqual(Created#book.created_at, Updated#book.created_at),
    ?assert(Updated#book.updated_at >= Created#book.updated_at),
    ?assertMatch(#book{title = <<"New">>, author = <<"B">>,
                       year = null, isbn = null}, Updated),
    %% ...and the change is durable, not just returned.
    ?assertEqual({ok, Updated}, book_store:get(Created#book.id)).

update_missing_returns_not_found() ->
    ?assertEqual({error, not_found},
                 book_store:update(4242, attrs(<<"T">>, <<"A">>))).

delete_removes_the_book() ->
    {ok, #book{id = Id}} = book_store:create(attrs(<<"T">>, <<"A">>)),
    ?assertEqual(ok, book_store:delete(Id)),
    ?assertEqual({error, not_found}, book_store:get(Id)).

delete_is_not_idempotent_by_design() ->
    {ok, #book{id = Id}} = book_store:create(attrs(<<"T">>, <<"A">>)),
    ?assertEqual(ok, book_store:delete(Id)),
    ?assertEqual({error, not_found}, book_store:delete(Id)).

count_tracks_the_table_size() ->
    ?assertEqual(0, book_store:count()),
    {ok, #book{id = Id}} = book_store:create(attrs(<<"T">>, <<"A">>)),
    ?assertEqual(1, book_store:count()),
    ok = book_store:delete(Id),
    ?assertEqual(0, book_store:count()).

%%%===================================================================
%%% Durability (own fixture: it restarts the store mid-test)
%%%===================================================================

durability_test_() ->
    {setup,
     fun() -> book_api_test_helper:fresh_db_dir(durability) end,
     fun(_Dir) -> book_store:stop() end,
     fun(Dir) ->
         {"books written before a restart are still there afterwards",
          fun() ->
              ok = book_store:init(Dir),
              ok = book_api_test_helper:reset_db(),
              {ok, #book{id = Id}} = book_store:create(attrs(<<"Dune">>, <<"FH">>)),

              ok = book_store:stop(),
              ok = book_store:init(Dir),

              ?assertMatch({ok, #book{title = <<"Dune">>}}, book_store:get(Id)),
              %% The id sequence survives too, so ids are never reused.
              {ok, #book{id = NextId}} = book_store:create(attrs(<<"Next">>, <<"FH">>)),
              ?assertEqual(Id + 1, NextId)
          end}
     end}.

%%%===================================================================
%%% Helpers
%%%===================================================================

attrs(Title, Author) ->
    #{title => Title, author => Author, year => null, isbn => null}.
