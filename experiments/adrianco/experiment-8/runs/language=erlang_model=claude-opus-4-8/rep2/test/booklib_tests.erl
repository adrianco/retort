%%% @doc EUnit tests for booklib. Covers the storage/validation layer directly
%%% and the full HTTP stack end-to-end via httpc.
-module(booklib_tests).

-include_lib("eunit/include/eunit.hrl").

%%====================================================================
%% Fixture: start a fresh application on an ephemeral port with a temp DB.
%%====================================================================

setup() ->
    %% Unique temp DB file per run so tests never share state.
    Unique = integer_to_list(erlang:unique_integer([positive])),
    DbFile = filename:join(test_tmp_dir(), "booklib_test_" ++ Unique ++ ".dets"),
    application:load(booklib),
    application:set_env(booklib, db_file, DbFile),
    application:set_env(booklib, port, 0),
    {ok, _} = application:ensure_all_started(booklib),
    {ok, _} = application:ensure_all_started(inets),
    Port = booklib_server:port(),
    #{port => Port, db_file => DbFile}.

cleanup(#{db_file := DbFile}) ->
    application:stop(booklib),
    application:unload(booklib),
    file:delete(DbFile),
    ok.

test_tmp_dir() ->
    case os:getenv("TMPDIR") of
        false -> "/tmp";
        Dir -> Dir
    end.

%%====================================================================
%% Direct DB / validation tests
%%====================================================================

db_test_() ->
    {setup, fun setup/0, fun cleanup/1,
     fun(_Ctx) ->
        [
         {"create then get a book", fun create_and_get/0},
         {"validation rejects missing fields", fun validation_required/0},
         {"author filter narrows the list", fun author_filter/0},
         {"update replaces fields", fun update_book/0},
         {"delete removes a book", fun delete_book/0}
        ]
     end}.

create_and_get() ->
    {ok, Book} = booklib_db:create(#{<<"title">> => <<"Dune">>,
                                     <<"author">> => <<"Herbert">>,
                                     <<"year">> => 1965,
                                     <<"isbn">> => <<"978-0">>}),
    Id = maps:get(<<"id">>, Book),
    ?assert(is_integer(Id)),
    ?assertEqual(<<"Dune">>, maps:get(<<"title">>, Book)),
    ?assertEqual({ok, Book}, booklib_db:get(Id)).

validation_required() ->
    ?assertMatch({error, {validation, _}},
                 booklib_db:create(#{<<"author">> => <<"Nobody">>})),
    ?assertMatch({error, {validation, _}},
                 booklib_db:create(#{<<"title">> => <<"  ">>,
                                     <<"author">> => <<"Nobody">>})),
    {error, {validation, Errors}} = booklib_db:create(#{}),
    ?assert(length(Errors) >= 2).

author_filter() ->
    {ok, _} = booklib_db:create(#{<<"title">> => <<"A">>, <<"author">> => <<"Asimov">>}),
    {ok, _} = booklib_db:create(#{<<"title">> => <<"B">>, <<"author">> => <<"Asimov">>}),
    {ok, _} = booklib_db:create(#{<<"title">> => <<"C">>, <<"author">> => <<"Clarke">>}),
    OnlyAsimov = booklib_db:list(<<"Asimov">>),
    ?assert(length(OnlyAsimov) >= 2),
    ?assert(lists:all(fun(B) -> maps:get(<<"author">>, B) =:= <<"Asimov">> end,
                      OnlyAsimov)),
    %% Case-insensitive match.
    ?assertEqual(length(OnlyAsimov), length(booklib_db:list(<<"asimov">>))).

update_book() ->
    {ok, Book} = booklib_db:create(#{<<"title">> => <<"Old">>,
                                     <<"author">> => <<"Auth">>}),
    Id = maps:get(<<"id">>, Book),
    {ok, Updated} = booklib_db:update(Id, #{<<"title">> => <<"New">>,
                                            <<"author">> => <<"Auth">>}),
    ?assertEqual(<<"New">>, maps:get(<<"title">>, Updated)),
    ?assertEqual(Id, maps:get(<<"id">>, Updated)),
    ?assertEqual({error, not_found},
                 booklib_db:update(999999, #{<<"title">> => <<"X">>,
                                             <<"author">> => <<"Y">>})).

delete_book() ->
    {ok, Book} = booklib_db:create(#{<<"title">> => <<"Temp">>,
                                     <<"author">> => <<"Auth">>}),
    Id = maps:get(<<"id">>, Book),
    ?assertEqual(ok, booklib_db:delete(Id)),
    ?assertEqual({error, not_found}, booklib_db:get(Id)),
    ?assertEqual({error, not_found}, booklib_db:delete(Id)).

%%====================================================================
%% End-to-end HTTP tests
%%====================================================================

http_test_() ->
    {setup, fun setup/0, fun cleanup/1,
     fun(Ctx) ->
        [
         {"health check", fun() -> health(Ctx) end},
         {"POST creates and GET retrieves", fun() -> create_flow(Ctx) end},
         {"POST with missing title is rejected", fun() -> invalid_create(Ctx) end},
         {"GET unknown id is 404", fun() -> missing_book(Ctx) end},
         {"PUT and DELETE lifecycle", fun() -> put_delete(Ctx) end}
        ]
     end}.

health(#{port := Port}) ->
    {Code, Body} = http_get(Port, "/health"),
    ?assertEqual(200, Code),
    ?assertEqual(<<"ok">>, maps:get(<<"status">>, Body)).

create_flow(#{port := Port}) ->
    Payload = #{<<"title">> => <<"1984">>, <<"author">> => <<"Orwell">>,
                <<"year">> => 1949},
    {Code, Book} = http_post(Port, "/books", Payload),
    ?assertEqual(201, Code),
    Id = maps:get(<<"id">>, Book),
    {GetCode, Got} = http_get(Port, "/books/" ++ integer_to_list(Id)),
    ?assertEqual(200, GetCode),
    ?assertEqual(<<"1984">>, maps:get(<<"title">>, Got)),
    {ListCode, Listing} = http_get(Port, "/books"),
    ?assertEqual(200, ListCode),
    ?assert(maps:get(<<"count">>, Listing) >= 1).

invalid_create(#{port := Port}) ->
    {Code, Body} = http_post(Port, "/books", #{<<"author">> => <<"Nobody">>}),
    ?assertEqual(422, Code),
    ?assertEqual(<<"validation failed">>, maps:get(<<"error">>, Body)).

missing_book(#{port := Port}) ->
    {Code, _Body} = http_get(Port, "/books/987654"),
    ?assertEqual(404, Code).

put_delete(#{port := Port}) ->
    {201, Book} = http_post(Port, "/books",
                            #{<<"title">> => <<"Draft">>, <<"author">> => <<"Me">>}),
    Id = maps:get(<<"id">>, Book),
    Path = "/books/" ++ integer_to_list(Id),
    {PutCode, Updated} = http_put(Port, Path,
                                  #{<<"title">> => <<"Final">>, <<"author">> => <<"Me">>}),
    ?assertEqual(200, PutCode),
    ?assertEqual(<<"Final">>, maps:get(<<"title">>, Updated)),
    {DelCode, _} = http_delete(Port, Path),
    ?assertEqual(200, DelCode),
    {GetCode, _} = http_get(Port, Path),
    ?assertEqual(404, GetCode).

%%====================================================================
%% HTTP client helpers (built on inets httpc)
%%====================================================================

base(Port) -> "http://127.0.0.1:" ++ integer_to_list(Port).

http_get(Port, Path) ->
    request(get, {base(Port) ++ Path, []}).

http_post(Port, Path, Map) ->
    request(post, {base(Port) ++ Path, [], "application/json", json:encode(Map)}).

http_put(Port, Path, Map) ->
    request(put, {base(Port) ++ Path, [], "application/json", json:encode(Map)}).

http_delete(Port, Path) ->
    request(delete, {base(Port) ++ Path, []}).

request(Method, Request) ->
    {ok, {{_Vsn, Code, _Reason}, _Headers, Body}} =
        httpc:request(Method, Request, [], [{body_format, binary}]),
    Decoded =
        case Body of
            <<>> -> #{};
            _ -> json:decode(Body)
        end,
    {Code, Decoded}.
