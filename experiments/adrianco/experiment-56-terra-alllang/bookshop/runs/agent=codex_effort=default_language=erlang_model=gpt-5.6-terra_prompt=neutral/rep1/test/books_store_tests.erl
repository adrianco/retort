-module(books_store_tests).
-include_lib("eunit/include/eunit.hrl").

store_test_() -> {setup, fun setup/0, fun cleanup/1, [fun create_and_get/0, fun filter_by_author/0, fun update_and_delete/0]}.
setup() -> File = filename:join("/tmp", "books_api_eunit.dets"), file:delete(File), {ok, _} = books_store:start_link(File), File.
cleanup(File) ->
    try books_store:stop() catch _:_ -> ok end,
    file:delete(File), ok.
create_and_get() -> {ok, B} = books_store:create(#{title => <<"Dune">>, author => <<"Frank Herbert">>, year => 1965}), ?assertEqual(1, maps:get(id, B)), ?assertEqual({ok, B}, books_store:get(1)).
filter_by_author() -> books_store:create(#{title => <<"A">>, author => <<"Ada">>}), books_store:create(#{title => <<"B">>, author => <<"Bob">>}), {ok, [Only]} = books_store:list(<<"Ada">>), ?assertEqual(<<"A">>, maps:get(title, Only)).
update_and_delete() -> {ok, B} = books_store:create(#{title => <<"Old">>, author => <<"Ada">>}), Id = maps:get(id, B), {ok, New} = books_store:update(Id, #{title => <<"New">>, author => <<"Ada">>}), ?assertEqual(<<"New">>, maps:get(title, New)), ok = books_store:delete(Id), ?assertEqual(not_found, books_store:get(Id)).
