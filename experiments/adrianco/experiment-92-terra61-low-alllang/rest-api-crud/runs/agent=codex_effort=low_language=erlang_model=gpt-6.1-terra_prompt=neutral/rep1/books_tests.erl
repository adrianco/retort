-module(books_tests).
-include_lib("eunit/include/eunit.hrl").

api_integration_test_() ->
    {setup, fun setup/0, fun cleanup/1, fun({unavailable, _}) -> []; (Port) -> [
        ?_test(crud(Port)),
        ?_test(validation(Port)),
        ?_test(persistence(Port))
    ] end}.
setup() ->
    File = "/tmp/books_test_" ++ integer_to_list(erlang:unique_integer([positive])) ++ ".dets",
    put(test_file, File),
    case books:start(0, File) of
        {ok, Port} -> {Port, File};
        {error, eperm} -> {unavailable, File}
    end.
cleanup({_Port, File}) -> books:stop(), file:delete(File).

crud({Port, _}) ->
    {200, #{<<"status">> := <<"ok">>}} = http(Port, "GET", "/health", ""),
    {201, Created} = http(Port, "POST", "/books", "{\"title\":\"One\",\"author\":\"Ada\",\"year\":2020,\"isbn\":\"123\"}"),
    Id = maps:get(<<"id">>, Created), Path = "/books/" ++ integer_to_list(Id),
    {200, Created} = http(Port, "GET", Path, ""),
    {200, [Created]} = http(Port, "GET", "/books?author=Ada", ""),
    {200, []} = http(Port, "GET", "/books?author=Other", ""),
    {200, Updated} = http(Port, "PUT", Path, "{\"title\":\"Two\",\"author\":\"Ada\"}"),
    ?assertEqual(<<"Two">>, maps:get(<<"title">>, Updated)),
    {200, _} = http(Port, "DELETE", Path, ""),
    {404, _} = http(Port, "GET", Path, "").
validation({Port, _}) ->
    {400, _} = http(Port, "POST", "/books", "{\"title\":\"One\"}"),
    {400, _} = http(Port, "POST", "/books", "{\"title\":\" \",\"author\":\"Ada\"}"),
    {400, _} = http(Port, "POST", "/books", "bad"),
    {404, _} = http(Port, "DELETE", "/books/999999", "").
persistence({Port, File}) ->
    {201, Book} = http(Port, "POST", "/books", "{\"title\":\"Persistent\",\"author\":\"Ada\"}"),
    Id = maps:get(<<"id">>, Book),
    books:stop(), {ok, NewPort} = books:start(0, File),
    {200, Book} = http(NewPort, "GET", "/books/" ++ integer_to_list(Id), "").
http(Port, Method, Path, Body) ->
    {ok, Socket} = gen_tcp:connect("localhost", Port, [binary, {active, false}]),
    ok = gen_tcp:send(Socket, [Method, " ", Path, " HTTP/1.1\r\nHost: localhost\r\nContent-Length: ", integer_to_list(length(Body)), "\r\n\r\n", Body]),
    Response = receive_all(Socket, <<>>),
    [Header, Json] = binary:split(Response, <<"\r\n\r\n">>),
    [StatusLine | _] = binary:split(Header, <<"\r\n">>, [global]),
    [_, Code | _] = binary:split(StatusLine, <<" ">>, [global]),
    {binary_to_integer(Code), json:decode(Json)}.
receive_all(Socket, Acc) -> case gen_tcp:recv(Socket, 0, 5000) of {ok, Data} -> receive_all(Socket, <<Acc/binary, Data/binary>>); {error, closed} -> Acc end.

unit_test_() ->
    {setup,
     fun() ->
         File = "/tmp/books_unit_" ++ integer_to_list(erlang:unique_integer([positive])) ++ ".dets",
         ok = books_store:start(File), File
     end,
     fun(File) -> books_store:stop(), file:delete(File) end,
     fun(File) -> [?_test(unit_crud()), ?_test(unit_validation()), ?_test(unit_persistence(File))] end}.
unit_crud() ->
    Body = <<"{\"title\":\"One\",\"author\":\"Ada\",\"year\":2020}">>,
    {201, B} = books:request(<<"POST">>, <<"/books">>, Body),
    Id = maps:get(id, B), Path = <<"/books/", (integer_to_binary(Id))/binary>>,
    ?assertEqual({200, B}, books:request(<<"GET">>, Path, <<>>)),
    ?assertEqual({200, [B]}, books:request(<<"GET">>, <<"/books?author=Ada">>, <<>>)),
    ?assertEqual({200, []}, books:request(<<"GET">>, <<"/books?author=Other">>, <<>>)),
    {200, Updated} = books:request(<<"PUT">>, Path, <<"{\"title\":\"New\",\"author\":\"Ada\"}">>),
    ?assertEqual(<<"New">>, maps:get(title, Updated)),
    {200, _} = books:request(<<"DELETE">>, Path, <<>>),
    {404, _} = books:request(<<"GET">>, Path, <<>>).
unit_validation() ->
    {400, _} = books:request(<<"POST">>, <<"/books">>, <<"{}">>),
    {400, _} = books:request(<<"POST">>, <<"/books">>, <<"invalid">>),
    {200, #{status := <<"ok">>}} = books:request(<<"GET">>, <<"/health">>, <<>>),
    {404, _} = books:request(<<"GET">>, <<"/books/9999">>, <<>>).
unit_persistence(File) ->
    {201, B} = books:request(<<"POST">>, <<"/books">>, <<"{\"title\":\"Persist\",\"author\":\"Ada\"}">>),
    ok = books_store:stop(), ok = books_store:start(File),
    ?assertEqual({ok, B}, books_store:get(maps:get(id, B))).
