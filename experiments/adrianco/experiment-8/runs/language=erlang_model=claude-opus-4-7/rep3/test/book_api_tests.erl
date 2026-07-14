-module(book_api_tests).

-include_lib("eunit/include/eunit.hrl").

-define(PORT, 8089).
-define(DB,   "test_books.dets").

%% --------------------------------------------------------------------
%% eunit setup / teardown
%% --------------------------------------------------------------------

api_test_() ->
    {setup,
     fun setup/0,
     fun cleanup/1,
     [
        {"health endpoint",         fun health_returns_ok/0},
        {"create + get a book",     fun create_and_get_book/0},
        {"list with author filter", fun list_books_filter_by_author/0},
        {"validation: missing title", fun create_requires_title/0},
        {"validation: missing author", fun create_requires_author/0},
        {"update a book",           fun update_book/0},
        {"delete a book",           fun delete_book/0},
        {"get unknown id 404",      fun get_unknown_book/0}
     ]}.

setup() ->
    ok = application:load(book_api),
    ok = application:set_env(book_api, port, ?PORT),
    ok = application:set_env(book_api, db_file, ?DB),
    file:delete(?DB),
    {ok, _} = application:ensure_all_started(book_api),
    {ok, _} = application:ensure_all_started(inets),
    ok.

cleanup(_) ->
    _ = application:stop(book_api),
    _ = application:unload(book_api),
    _ = file:delete(?DB),
    ok.

%% --------------------------------------------------------------------
%% test cases
%% --------------------------------------------------------------------

health_returns_ok() ->
    {Code, Body} = http_get("/health"),
    ?assertEqual(200, Code),
    ?assertEqual(<<"ok">>, maps:get(<<"status">>, decode(Body))).

create_and_get_book() ->
    Payload = #{title => <<"Programming Erlang">>,
                author => <<"Joe Armstrong">>,
                year => 2007,
                isbn => <<"978-1937785536">>},
    {201, RespBody} = http_post("/books", Payload),
    Book = decode(RespBody),
    Id = maps:get(<<"id">>, Book),
    ?assert(is_integer(Id)),
    ?assertEqual(<<"Programming Erlang">>, maps:get(<<"title">>, Book)),

    {200, GetBody} = http_get("/books/" ++ integer_to_list(Id)),
    Got = decode(GetBody),
    ?assertEqual(<<"Programming Erlang">>, maps:get(<<"title">>, Got)),
    ?assertEqual(<<"Joe Armstrong">>, maps:get(<<"author">>, Got)),
    ?assertEqual(2007, maps:get(<<"year">>, Got)).

list_books_filter_by_author() ->
    {201, _} = http_post("/books", #{title => <<"A1">>, author => <<"Alice">>}),
    {201, _} = http_post("/books", #{title => <<"A2">>, author => <<"Alice">>}),
    {201, _} = http_post("/books", #{title => <<"B1">>, author => <<"Bob">>}),

    {200, AllBody} = http_get("/books"),
    All = decode(AllBody),
    ?assert(is_list(All)),
    ?assert(length(All) >= 3),

    {200, AliceBody} = http_get("/books?author=Alice"),
    AliceBooks = decode(AliceBody),
    ?assert(is_list(AliceBooks)),
    ?assert(length(AliceBooks) >= 2),
    ?assert(lists:all(
        fun(B) -> maps:get(<<"author">>, B) =:= <<"Alice">> end,
        AliceBooks)).

create_requires_title() ->
    {Code, Body} = http_post("/books", #{author => <<"NoTitle">>}),
    ?assertEqual(400, Code),
    ?assertEqual(<<"title is required">>, maps:get(<<"error">>, decode(Body))).

create_requires_author() ->
    {Code, Body} = http_post("/books", #{title => <<"No Author">>}),
    ?assertEqual(400, Code),
    ?assertEqual(<<"author is required">>, maps:get(<<"error">>, decode(Body))).

update_book() ->
    {201, CreateBody} = http_post("/books",
        #{title => <<"Old Title">>, author => <<"Author A">>}),
    Id = maps:get(<<"id">>, decode(CreateBody)),

    {200, UpdBody} = http_put("/books/" ++ integer_to_list(Id),
        #{title => <<"New Title">>, author => <<"Author B">>, year => 2020}),
    Updated = decode(UpdBody),
    ?assertEqual(<<"New Title">>, maps:get(<<"title">>, Updated)),
    ?assertEqual(<<"Author B">>, maps:get(<<"author">>, Updated)),
    ?assertEqual(2020, maps:get(<<"year">>, Updated)).

delete_book() ->
    {201, CreateBody} = http_post("/books",
        #{title => <<"Doomed">>, author => <<"X">>}),
    Id = maps:get(<<"id">>, decode(CreateBody)),
    {204, _} = http_delete("/books/" ++ integer_to_list(Id)),
    {404, _} = http_get("/books/" ++ integer_to_list(Id)).

get_unknown_book() ->
    {Code, _} = http_get("/books/999999"),
    ?assertEqual(404, Code).

%% --------------------------------------------------------------------
%% helpers
%% --------------------------------------------------------------------

base_url() ->
    "http://localhost:" ++ integer_to_list(?PORT).

decode(Body) when is_list(Body) ->
    jsone:decode(list_to_binary(Body));
decode(Body) when is_binary(Body) ->
    jsone:decode(Body).

http_get(Path) ->
    do_request(get, {base_url() ++ Path, []}).

http_delete(Path) ->
    do_request(delete, {base_url() ++ Path, []}).

http_post(Path, Map) ->
    Body = binary_to_list(jsone:encode(Map)),
    do_request(post, {base_url() ++ Path, [], "application/json", Body}).

http_put(Path, Map) ->
    Body = binary_to_list(jsone:encode(Map)),
    do_request(put, {base_url() ++ Path, [], "application/json", Body}).

do_request(Method, Req) ->
    {ok, {{_, Code, _}, _Hdrs, Body}} =
        httpc:request(Method, Req, [], []),
    {Code, Body}.
