%% Integration tests: start the full application on a test port and
%% exercise the HTTP API with httpc. Also unit tests for validation.
-module(books_api_tests).

-include_lib("eunit/include/eunit.hrl").

-define(PORT, 8199).
-define(BASE, "http://127.0.0.1:8199").

%%% Fixture ------------------------------------------------------------------

api_test_() ->
    {setup, fun start/0, fun stop/1,
     fun(_) ->
         {inorder,
          [{"health check", fun health_check/0},
           {"create and fetch a book", fun create_and_get/0},
           {"validation rejects missing fields", fun validation_errors/0},
           {"list all and filter by author", fun list_and_filter/0},
           {"update a book", fun update_book/0},
           {"delete a book", fun delete_book/0},
           {"unknown id returns 404", fun missing_book/0},
           {"malformed body returns 400", fun malformed_body/0}]}
     end}.

start() ->
    DataFile = filename:join(element(2, file:get_cwd()),
                             "books_test_" ++ integer_to_list(?PORT) ++ ".dets"),
    file:delete(DataFile),
    %% persistent, so loading the .app file does not overwrite these
    application:set_env(books, port, ?PORT, [{persistent, true}]),
    application:set_env(books, data_file, DataFile, [{persistent, true}]),
    {ok, Apps} = application:ensure_all_started(books),
    {ok, _} = application:ensure_all_started(inets),
    {Apps, DataFile}.

stop({Apps, DataFile}) ->
    [application:stop(App) || App <- lists:reverse(Apps)],
    file:delete(DataFile),
    ok.

%%% Tests ---------------------------------------------------------------------

health_check() ->
    {200, Body} = req(get, "/health"),
    ?assertEqual(#{<<"status">> => <<"ok">>}, Body).

create_and_get() ->
    {201, Created} = req(post, "/books",
                         #{title => <<"The Mythical Man-Month">>,
                           author => <<"Fred Brooks">>,
                           year => 1975,
                           isbn => <<"978-0201835953">>}),
    Id = maps:get(<<"id">>, Created),
    ?assert(is_integer(Id)),
    ?assertEqual(<<"The Mythical Man-Month">>, maps:get(<<"title">>, Created)),
    ?assertEqual(1975, maps:get(<<"year">>, Created)),
    {200, Fetched} = req(get, "/books/" ++ integer_to_list(Id)),
    ?assertEqual(Created, Fetched).

validation_errors() ->
    {400, Body1} = req(post, "/books", #{author => <<"Anon">>}),
    ?assert(lists:member(<<"title is required">>, maps:get(<<"errors">>, Body1))),
    {400, Body2} = req(post, "/books", #{title => <<"  ">>, author => <<"Anon">>}),
    ?assert(lists:member(<<"title must not be empty">>, maps:get(<<"errors">>, Body2))),
    {400, Body3} = req(post, "/books", #{title => <<"T">>, author => <<"A">>,
                                         year => <<"not a number">>}),
    ?assert(lists:member(<<"year must be an integer">>, maps:get(<<"errors">>, Body3))).

list_and_filter() ->
    {201, _} = req(post, "/books", #{title => <<"SICP">>,
                                     author => <<"Abelson">>}),
    {201, _} = req(post, "/books", #{title => <<"HtDP">>,
                                     author => <<"Felleisen">>}),
    {200, All} = req(get, "/books"),
    ?assert(length(All) >= 3),
    {200, Filtered} = req(get, "/books?author=Abelson"),
    ?assertEqual(1, length(Filtered)),
    [Only] = Filtered,
    ?assertEqual(<<"SICP">>, maps:get(<<"title">>, Only)).

update_book() ->
    {201, Created} = req(post, "/books", #{title => <<"Draft">>,
                                           author => <<"Someone">>}),
    Id = maps:get(<<"id">>, Created),
    Path = "/books/" ++ integer_to_list(Id),
    {200, Updated} = req(put, Path, #{title => <<"Final">>,
                                      author => <<"Someone">>,
                                      year => 2026}),
    ?assertEqual(<<"Final">>, maps:get(<<"title">>, Updated)),
    ?assertEqual(2026, maps:get(<<"year">>, Updated)),
    ?assertEqual(Id, maps:get(<<"id">>, Updated)),
    {200, Fetched} = req(get, Path),
    ?assertEqual(Updated, Fetched),
    %% invalid update payload is rejected and leaves the record intact
    {400, _} = req(put, Path, #{author => <<"Someone">>}),
    {200, Fetched} = req(get, Path).

delete_book() ->
    {201, Created} = req(post, "/books", #{title => <<"Ephemeral">>,
                                           author => <<"Nobody">>}),
    Id = maps:get(<<"id">>, Created),
    Path = "/books/" ++ integer_to_list(Id),
    {204, no_body} = req(delete, Path),
    {404, _} = req(get, Path),
    {404, _} = req(delete, Path).

missing_book() ->
    {404, _} = req(get, "/books/999999"),
    {404, _} = req(get, "/books/not-an-id"),
    {404, _} = req(put_raw, "/books/999999",
                   json:encode(#{title => <<"X">>, author => <<"Y">>})).

malformed_body() ->
    {400, _} = req(post_raw, "/books", <<"this is not json">>),
    {400, _} = req(post_raw, "/books", <<"[1,2,3]">>).

%%% HTTP helpers ---------------------------------------------------------------

req(Method, Path) ->
    req(Method, Path, undefined).

req(get, Path, undefined) ->
    do(httpc:request(get, {?BASE ++ Path, []}, [], [{body_format, binary}]));
req(delete, Path, undefined) ->
    do(httpc:request(delete, {?BASE ++ Path, []}, [], [{body_format, binary}]));
req(post, Path, Map) ->
    req(post_raw, Path, iolist_to_binary(json:encode(Map)));
req(put, Path, Map) ->
    req(put_raw, Path, iolist_to_binary(json:encode(Map)));
req(post_raw, Path, Body) ->
    do(httpc:request(post, {?BASE ++ Path, [], "application/json", Body},
                     [], [{body_format, binary}]));
req(put_raw, Path, Body) ->
    do(httpc:request(put, {?BASE ++ Path, [], "application/json", Body},
                     [], [{body_format, binary}])).

do({ok, {{_, Status, _}, _Headers, <<>>}}) ->
    {Status, no_body};
do({ok, {{_, Status, _}, _Headers, Body}}) ->
    {Status, json:decode(Body)}.
