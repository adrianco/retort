-module(books_tests).
-include_lib("eunit/include/eunit.hrl").

api_test_() -> {setup, fun setup/0, fun cleanup/1, fun({Db, Server}) -> [?_test(crud(Db)), ?_test(validation(Db)), ?_test(filter(Db)), ?_test(http(Server))] end}.
setup() ->
    Db = filename:join("/tmp", "books_test_" ++ integer_to_list(erlang:unique_integer([positive])) ++ ".db"),
    _ = os:cmd("sqlite3 " ++ Db ++ " 'CREATE TABLE books (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, author TEXT NOT NULL, year INTEGER, isbn TEXT);'"),
    Server = case books:start(0, Db) of {ok, S} -> S; {error, eperm} -> unavailable end, {Db, Server}.
cleanup({Db, Server}) -> case Server of unavailable -> ok; _ -> books:stop(Server) end, file:delete(Db).
crud(Db) ->
    {201, Created} = books:handle(<<"POST">>, <<"/books">>, <<"{\"title\":\"One\",\"author\":\"A\",\"year\":2020,\"isbn\":\"x\"}">>, Db),
    Id = integer_to_binary(maps:get(<<"id">>, Created)), Path = <<"/books/", Id/binary>>,
    ?assertMatch({200, #{<<"title">> := <<"One">>}}, books:handle(<<"GET">>, Path, <<>>, Db)),
    ?assertMatch({200, #{<<"title">> := <<"Two">>}}, books:handle(<<"PUT">>, Path, <<"{\"title\":\"Two\",\"author\":\"B\"}">>, Db)),
    ?assertMatch({200, _}, books:handle(<<"DELETE">>, Path, <<>>, Db)),
    ?assertMatch({404, _}, books:handle(<<"GET">>, Path, <<>>, Db)).
validation(Db) ->
    ?assertMatch({400, _}, books:handle(<<"POST">>, <<"/books">>, <<"{\"title\":\"x\"}">>, Db)),
    ?assertMatch({400, _}, books:handle(<<"POST">>, <<"/books">>, <<"not json">>, Db)),
    ?assertMatch({400, _}, books:handle(<<"POST">>, <<"/books">>, <<"{\"title\":\" \",\"author\":\"A\"}">>, Db)).
filter(Db) ->
    {201, _} = books:handle(<<"POST">>, <<"/books">>, <<"{\"title\":\"T\",\"author\":\"Jane Doe\"}">>, Db),
    {200, Rows} = books:handle(<<"GET">>, <<"/books?author=Jane%20Doe">>, <<>>, Db),
    ?assertEqual(1, length(Rows)),
    ?assertMatch({200, []}, books:handle(<<"GET">>, <<"/books?author=Other">>, <<>>, Db)).
http(unavailable) -> ok;
http({_, Socket}) ->
    {ok, {_, Port}} = inet:sockname(Socket),
    {ok, Client} = gen_tcp:connect("localhost", Port, [binary, {active, false}]),
    ok = gen_tcp:send(Client, <<"GET /health HTTP/1.1\r\nHost: localhost\r\n\r\n">>),
    {ok, Response} = gen_tcp:recv(Client, 0, 5000),
    ?assertMatch({_, _}, binary:match(Response, <<"200 OK">>)),
    ?assertMatch({_, _}, binary:match(Response, <<"\"status\":\"ok\"">>)),
    gen_tcp:close(Client).
