-module(books).
-export([start/0, start/2, stop/1, handle/4]).

start() ->
    Port = case os:getenv("PORT") of false -> 8080; P -> list_to_integer(P) end,
    Db = case os:getenv("BOOKS_DB") of false -> "books.db"; D -> D end,
    {ok, _} = start(Port, Db),
    io:format("Listening on port ~p~n", [Port]),
    receive stop -> ok end.

start(Port, Db) ->
    case db(Db, "CREATE TABLE IF NOT EXISTS books (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, author TEXT NOT NULL, year INTEGER, isbn TEXT);") of
        {ok, _} ->
            case gen_tcp:listen(Port, [binary, {packet, raw}, {active, false}, {reuseaddr, true}]) of
                {ok, Socket} ->
                    Pid = spawn(fun() -> accept(Socket, Db) end),
                    {ok, {Pid, Socket}};
                Error -> Error
            end;
        Error -> Error
    end.
stop({Pid, Socket}) -> gen_tcp:close(Socket), exit(Pid, shutdown), ok.

accept(Socket, Db) ->
    case gen_tcp:accept(Socket) of
        {ok, Client} -> spawn(fun() -> serve(Client, Db) end), accept(Socket, Db);
        {error, closed} -> ok;
        {error, _} -> accept(Socket, Db)
    end.
serve(Socket, Db) ->
    try
        Response = case read_request(Socket, <<>>) of
            {ok, Method, Target, Body} -> handle(Method, Target, Body, Db);
            _ -> {400, #{error => <<"Invalid request">>}}
        end,
        {Status, Payload} = Response,
        Json = json:encode(Payload),
        gen_tcp:send(Socket, ["HTTP/1.1 ", integer_to_list(Status), " ", reason(Status), "\r\nContent-Type: application/json\r\nConnection: close\r\nContent-Length: ", integer_to_list(iolist_size(Json)), "\r\n\r\n", Json])
    catch _:_ -> ok end,
    gen_tcp:close(Socket).
read_request(Socket, Acc) when byte_size(Acc) =< 1048576 ->
    case binary:match(Acc, <<"\r\n\r\n">>) of
        nomatch -> case gen_tcp:recv(Socket, 0, 5000) of {ok, B} -> read_request(Socket, <<Acc/binary, B/binary>>); E -> E end;
        {Pos, 4} ->
            <<Head:Pos/binary, _:4/binary, Body/binary>> = Acc,
            [First | Headers] = binary:split(Head, <<"\r\n">>, [global]),
            case binary:split(First, <<" ">>, [global]) of
                [Method, Target, _] ->
                    Lengths = [string:trim(V) || H <- Headers, [K,V] <- [binary:split(H, <<":">>)], string:lowercase(K) =:= <<"content-length">>],
                    Length = case Lengths of [] -> 0; [L] -> binary_to_integer(L) end,
                    true = Length >= 0 andalso Length =< 1048576,
                    case read_body(Socket, Body, Length) of {ok, B} -> {ok, Method, Target, B}; E -> E end;
                _ -> error
            end
    end;
read_request(_, _) -> error.
read_body(_, Body, Length) when byte_size(Body) >= Length -> {ok, binary:part(Body, 0, Length)};
read_body(Socket, Body, Length) -> case gen_tcp:recv(Socket, 0, 5000) of {ok, B} -> read_body(Socket, <<Body/binary, B/binary>>, Length); E -> E end.

handle(Method, Target, Body, Db) ->
    try route(Method, binary:split(Target, <<"?">>), Body, Db)
    catch _:_ -> {500, #{error => <<"Internal server error">>}} end.
route(<<"GET">>, [<<"/health">>], _, _) -> {200, #{status => <<"ok">>}};
route(<<"POST">>, [<<"/books">>], Body, Db) ->
    case validate(Body) of
        {ok, B} ->
            Sql = ["INSERT INTO books (title,author,year,isbn) VALUES (", values(B), ") RETURNING *;"],
            one_result(db(Db, Sql), 201);
        error -> bad_request()
    end;
route(<<"GET">>, [<<"/books">> | Query], _, Db) ->
    Filter = case Query of [] -> ""; [Q] -> author_filter(Q) end,
    case db(Db, ["SELECT * FROM books", Filter, " ORDER BY id;"]) of
        {ok, Rows} -> {200, Rows}; _ -> server_error()
    end;
route(Method, [Path], Body, Db) ->
    case binary:split(Path, <<"/">>, [global]) of
        [<<>>, <<"books">>, IdBin] ->
            case valid_id(IdBin) of
                true -> item(Method, IdBin, Body, Db);
                false -> not_found()
            end;
        _ -> not_found()
    end;
route(_, _, _, _) -> not_found().
item(<<"GET">>, Id, _, Db) -> one_result(db(Db, ["SELECT * FROM books WHERE id=", Id, ";"]), 200);
item(<<"DELETE">>, Id, _, Db) -> one_result(db(Db, ["DELETE FROM books WHERE id=", Id, " RETURNING *;"]), 200);
item(<<"PUT">>, Id, Body, Db) ->
    case validate(Body) of
        {ok, B} -> one_result(db(Db, ["UPDATE books SET (title,author,year,isbn) = (", values(B), ") WHERE id=", Id, " RETURNING *;"]), 200);
        error -> bad_request()
    end;
item(_, _, _, _) -> {405, #{error => <<"Method not allowed">>}}.
valid_id(<<>>) -> false;
valid_id(B) -> lists:all(fun(C) -> C >= $0 andalso C =< $9 end, binary_to_list(B)).
author_filter(Q) ->
    Pairs = uri_string:dissect_query(Q),
    case lists:keyfind(<<"author">>, 1, Pairs) of
        {_, Author} -> [" WHERE author=", sql_text(Author)]; false -> ""
    end.
validate(Body) ->
    try
        B = json:decode(Body),
        true = is_map(B),
        Title = maps:get(<<"title">>, B), Author = maps:get(<<"author">>, B),
        true = is_binary(Title) andalso byte_size(string:trim(Title)) > 0,
        true = is_binary(Author) andalso byte_size(string:trim(Author)) > 0,
        Year = maps:get(<<"year">>, B, null), Isbn = maps:get(<<"isbn">>, B, null),
        true = (Year =:= null orelse is_integer(Year)),
        true = (Isbn =:= null orelse is_binary(Isbn)),
        {ok, {Title, Author, Year, Isbn}}
    catch _:_ -> error end.
values({Title, Author, Year, Isbn}) -> [sql_text(Title), ",", sql_text(Author), ",", sql_value(Year), ",", sql_value(Isbn)].
sql_value(null) -> "NULL";
sql_value(N) when is_integer(N) -> integer_to_list(N);
sql_value(B) -> sql_text(B).
sql_text(B) -> ["CAST(X'", binary:encode_hex(B), "' AS TEXT)"].
one_result({ok, [Row]}, Status) -> {Status, Row};
one_result({ok, []}, _) -> not_found();
one_result(_, _) -> server_error().
bad_request() -> {400, #{error => <<"title and author are required; year must be an integer and isbn a string">>}}.
not_found() -> {404, #{error => <<"Not found">>}}.
server_error() -> {500, #{error => <<"Database error">>}}.
reason(200) -> "OK"; reason(201) -> "Created"; reason(400) -> "Bad Request"; reason(404) -> "Not Found"; reason(405) -> "Method Not Allowed"; reason(500) -> "Internal Server Error".

db(Path, Sql) ->
    Port = open_port({spawn_executable, os:find_executable("sqlite3")}, [binary, exit_status, use_stdio, stderr_to_stdout, {args, ["-json", "-cmd", ".timeout 5000", Path, iolist_to_binary(Sql)]}]),
    collect(Port, <<>>).
collect(Port, Acc) ->
    receive
        {Port, {data, Data}} -> collect(Port, <<Acc/binary, Data/binary>>);
        {Port, {exit_status, 0}} ->
            case string:trim(Acc) of <<>> -> {ok, []}; Json -> try {ok, json:decode(Json)} catch _:_ -> {error, invalid_database_response} end end;
        {Port, {exit_status, _}} -> {error, Acc}
    after 10000 -> port_close(Port), {error, timeout}
    end.
