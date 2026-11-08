-module(books_tests).
-include_lib("eunit/include/eunit.hrl").

validation_test() ->
    ?assertMatch({error, _}, books_handler:validate(#{})),
    ?assertMatch({error, _}, books_handler:validate(#{<<"title">> => <<" ">>, <<"author">> => <<"A">>})),
    ?assertMatch({error, _}, books_handler:validate(#{<<"title">> => <<"T">>, <<"author">> => <<"A">>, <<"year">> => <<"2000">>})),
    ?assertMatch({error, _}, books_handler:validate([])),
    ?assertMatch({ok, _}, books_handler:validate(#{<<"title">> => <<"T">>, <<"author">> => <<"A">>})).

store_test_() -> {setup, fun setup/0, fun cleanup/1, fun(_) -> [
    fun lifecycle/0, fun filtering/0, fun persistence/0
] end}.
setup() ->
    File = filename:join(os:getenv("TMPDIR", "/tmp"), "books_test_" ++ integer_to_list(erlang:unique_integer([positive])) ++ ".dets"),
    application:set_env(books, db_file, File), {ok, Pid} = books_store:start_link(), unlink(Pid), File.
cleanup(File) -> gen_server:stop(books_store), file:delete(File), ok.
book(Title, Author) -> #{<<"title">> => Title, <<"author">> => Author, <<"year">> => null, <<"isbn">> => null}.
lifecycle() ->
    {ok, Created} = books_store:create(book(<<"Dune">>, <<"Herbert">>)),
    Id = maps:get(<<"id">>, Created),
    ?assertEqual({ok, Created}, books_store:get(Id)),
    {ok, Updated} = books_store:update(Id, book(<<"New">>, <<"Writer">>)),
    ?assertEqual(<<"New">>, maps:get(<<"title">>, Updated)),
    ?assertEqual(ok, books_store:delete(Id)),
    ?assertEqual(not_found, books_store:get(Id)),
    ?assertEqual(not_found, books_store:delete(Id)),
    ?assertEqual(not_found, books_store:update(Id, book(<<"T">>, <<"A">>))).
filtering() ->
    {ok, A} = books_store:create(book(<<"One">>, <<"Author A">>)),
    {ok, B} = books_store:create(book(<<"Two">>, <<"Author B">>)),
    ?assertEqual([A], books_store:list(<<"Author A">>)),
    ?assertEqual([A, B], books_store:list(undefined)),
    ?assertEqual([], books_store:list(<<"Nobody">>)).
persistence() ->
    {ok, Created} = books_store:create(book(<<"Persist">>, <<"A">>)),
    Id = maps:get(<<"id">>, Created),
    ok = gen_server:stop(books_store), {ok, Pid} = books_store:start_link(), unlink(Pid),
    ?assertEqual({ok, Created}, books_store:get(Id)),
    {ok, Next} = books_store:create(book(<<"Next">>, <<"A">>)),
    ?assert(maps:get(<<"id">>, Next) > Id).
