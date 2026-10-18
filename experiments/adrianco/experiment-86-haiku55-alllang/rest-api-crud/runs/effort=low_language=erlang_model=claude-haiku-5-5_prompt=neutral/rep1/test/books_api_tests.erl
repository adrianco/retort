%% End-to-end tests: start the whole application against a temporary SQLite
%% file and exercise the HTTP API with httpc.
-module(books_api_tests).

-include_lib("eunit/include/eunit.hrl").

-define(PORT, 18765).
-define(BASE, "http://localhost:18765").

api_test_() ->
    {setup, fun setup/0, fun teardown/1,
     fun(_) ->
         [?_test(health_check()),
          ?_test(create_and_fetch_book()),
          ?_test(create_rejects_invalid_input()),
          ?_test(create_rejects_malformed_json()),
          ?_test(list_and_filter_by_author()),
          ?_test(update_replaces_book()),
          ?_test(update_validates_and_handles_missing()),
          ?_test(delete_removes_book()),
          ?_test(unknown_ids_and_methods()),
          ?_test(unknown_route_is_404())]
     end}.

setup() ->
    {ok, _} = application:ensure_all_started(inets),
    DbPath = filename:join(tmp_dir(), "books_test_" ++ integer_to_list(erlang:unique_integer([positive])) ++ ".db"),
    application:load(books),
    ok = application:set_env(books, port, ?PORT),
    ok = application:set_env(books, db_path, DbPath),
    {ok, _} = application:ensure_all_started(books),
    DbPath.

teardown(DbPath) ->
    ok = application:stop(books),
    _ = file:delete(DbPath),
    ok.

health_check() ->
    {200, Body} = request(get, "/health"),
    ?assertEqual(#{<<"status">> => <<"ok">>}, Body).

create_and_fetch_book() ->
    {201, Created} = request(post, "/books",
                             #{<<"title">> => <<"Dune">>,
                               <<"author">> => <<"Frank Herbert">>,
                               <<"year">> => 1965,
                               <<"isbn">> => <<"9780441172719">>}),
    Id = maps:get(<<"id">>, Created),
    ?assert(is_integer(Id)),
    ?assertEqual(#{<<"id">> => Id, <<"title">> => <<"Dune">>,
                   <<"author">> => <<"Frank Herbert">>, <<"year">> => 1965,
                   <<"isbn">> => <<"9780441172719">>}, Created),
    {200, Fetched} = request(get, "/books/" ++ integer_to_list(Id)),
    ?assertEqual(Created, Fetched).

create_rejects_invalid_input() ->
    {400, Resp} = request(post, "/books", #{<<"author">> => <<"Someone">>}),
    ?assertEqual(<<"validation failed">>, maps:get(<<"error">>, Resp)),
    ?assertEqual([<<"title is required">>], maps:get(<<"details">>, Resp)),
    {400, _} = request(post, "/books", #{<<"title">> => <<"No author">>}),
    {400, _} = request(post, "/books", [1, 2, 3]).

create_rejects_malformed_json() ->
    {400, Resp} = raw_request(post, "/books", <<"{not json">>),
    ?assertEqual(<<"request body must be valid JSON">>, maps:get(<<"error">>, Resp)).

list_and_filter_by_author() ->
    {201, _} = request(post, "/books", book(<<"Emma">>, <<"Jane Austen">>)),
    {201, _} = request(post, "/books", book(<<"Persuasion">>, <<"Jane Austen">>)),
    {201, _} = request(post, "/books", book(<<"Hyperion">>, <<"Dan Simmons">>)),
    {200, All} = request(get, "/books"),
    ?assert(length(All) >= 3),
    {200, Austen} = request(get, "/books?author=Jane%20Austen"),
    ?assertEqual([<<"Emma">>, <<"Persuasion">>],
                 [maps:get(<<"title">>, B) || B <- Austen]),
    {200, Insensitive} = request(get, "/books?author=jane%20austen"),
    ?assertEqual(2, length(Insensitive)),
    {200, None} = request(get, "/books?author=Nobody"),
    ?assertEqual([], None).

update_replaces_book() ->
    {201, Created} = request(post, "/books", book(<<"Old title">>, <<"Author A">>)),
    Path = "/books/" ++ integer_to_list(maps:get(<<"id">>, Created)),
    {200, Updated} = request(put, Path, book(<<"New title">>, <<"Author B">>)),
    ?assertEqual(maps:get(<<"id">>, Created), maps:get(<<"id">>, Updated)),
    ?assertEqual(<<"New title">>, maps:get(<<"title">>, Updated)),
    ?assertEqual(<<"Author B">>, maps:get(<<"author">>, Updated)),
    ?assertEqual(null, maps:get(<<"year">>, Updated)),
    {200, Fetched} = request(get, Path),
    ?assertEqual(Updated, Fetched).

update_validates_and_handles_missing() ->
    {201, Created} = request(post, "/books", book(<<"T">>, <<"A">>)),
    Path = "/books/" ++ integer_to_list(maps:get(<<"id">>, Created)),
    {400, _} = request(put, Path, #{<<"title">> => <<"">>, <<"author">> => <<"A">>}),
    {404, _} = request(put, "/books/999999", book(<<"T">>, <<"A">>)).

delete_removes_book() ->
    {201, Created} = request(post, "/books", book(<<"Gone">>, <<"Nobody">>)),
    Path = "/books/" ++ integer_to_list(maps:get(<<"id">>, Created)),
    {204, _} = request(delete, Path),
    {404, _} = request(get, Path),
    {404, _} = request(delete, Path).

unknown_ids_and_methods() ->
    {404, _} = request(get, "/books/999999"),
    {404, _} = request(get, "/books/abc"),
    {404, _} = request(get, "/books/0"),
    {405, _} = request(put, "/books", #{}),
    {405, _} = request(post, "/books/1", #{}),
    {405, _} = request(delete, "/books").

unknown_route_is_404() ->
    {404, _} = request(get, "/nope").

book(Title, Author) ->
    #{<<"title">> => Title, <<"author">> => Author}.

tmp_dir() ->
    case os:getenv("TMPDIR") of
        false -> "/tmp";
        Dir -> Dir
    end.

%% Helpers ---------------------------------------------------------------

request(Method, Path) ->
    raw_request(Method, Path, undefined).

request(Method, Path, Payload) ->
    raw_request(Method, Path, iolist_to_binary(json:encode(Payload))).

raw_request(Method, Path, Body) when Method =:= get; Method =:= delete; Body =:= undefined ->
    send(Method, {?BASE ++ Path, []});
raw_request(Method, Path, Body) ->
    send(Method, {?BASE ++ Path, [], "application/json", Body}).

send(Method, Request) ->
    {ok, {{_, Status, _}, _Headers, RespBody}} =
        httpc:request(Method, Request, [], [{body_format, binary}]),
    {Status, decode(RespBody)}.

decode(<<>>) -> <<>>;
decode(Bin) -> json:decode(Bin).
