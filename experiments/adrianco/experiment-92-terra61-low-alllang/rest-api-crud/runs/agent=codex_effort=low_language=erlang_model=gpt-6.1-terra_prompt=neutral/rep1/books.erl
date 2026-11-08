-module(books).
-export([start/0, start/2, stop/0, request/3]).

start() ->
    Port = list_to_integer(os:getenv("PORT", "8080")),
    start(Port, os:getenv("BOOKS_DB", "books.dets")).

start(Port, File) ->
    case books_store:start(File) of
        ok ->
            case gen_tcp:listen(Port, [binary, {packet, raw}, {active, false}, {reuseaddr, true}]) of
                {ok, Socket} ->
                    Pid = spawn(fun() -> receive {listen, S} -> accept(S) end end),
                    ok = gen_tcp:controlling_process(Socket, Pid),
                    Pid ! {listen, Socket},
                    register(books_listener, Pid),
                    {ok, {_, ActualPort}} = inet:sockname(Socket),
                    {ok, ActualPort};
                Error -> books_store:stop(), Error
            end;
        Error -> Error
    end.

stop() ->
    case whereis(books_listener) of undefined -> ok; Pid -> exit(Pid, kill) end,
    books_store:stop().

accept(Socket) ->
    case gen_tcp:accept(Socket) of
        {ok, Client} -> spawn(fun() -> serve(Client) end), accept(Socket);
        {error, closed} -> ok;
        {error, _} -> accept(Socket)
    end.

serve(Socket) ->
    Result = try read_request(Socket) catch _:_ -> {error, bad_request} end,
    {Status, Body} = case Result of
        {ok, Method, Path, Data} ->
            try request(Method, Path, Data) catch _:_ -> {500, #{error => <<"Internal server error">>}} end;
        {error, _} -> {400, #{error => <<"Bad request">>}}
    end,
    Encoded = json:encode(Body),
    gen_tcp:send(Socket, ["HTTP/1.1 ", integer_to_list(Status), " ", reason(Status), "\r\nContent-Type: application/json\r\nConnection: close\r\nContent-Length: ", integer_to_list(iolist_size(Encoded)), "\r\n\r\n", Encoded]),
    gen_tcp:close(Socket).

read_request(Socket) -> read_headers(Socket, <<>>).
read_headers(Socket, Buffer) when byte_size(Buffer) =< 65536 ->
    case binary:match(Buffer, <<"\r\n\r\n">>) of
        {Pos, 4} ->
            <<Head:Pos/binary, _:4/binary, Rest/binary>> = Buffer,
            [Line | Headers] = binary:split(Head, <<"\r\n">>, [global]),
            [Method, Path, _] = binary:split(Line, <<" ">>, [global]),
            Length = content_length(Headers),
            true = Length >= 0 andalso Length =< 1048576,
            {ok, Body} = read_body(Socket, Rest, Length),
            {ok, Method, Path, Body};
        nomatch ->
            case gen_tcp:recv(Socket, 0, 5000) of {ok, More} -> read_headers(Socket, <<Buffer/binary, More/binary>>); Error -> Error end
    end;
read_headers(_, _) -> {error, too_large}.

content_length(Headers) ->
    lists:foldl(fun(Header, Acc) ->
        case binary:split(Header, <<":">>) of
            [Name, Value] -> case string:lowercase(Name) of <<"content-length">> -> binary_to_integer(string:trim(Value)); _ -> Acc end;
            _ -> Acc
        end
    end, 0, Headers).
read_body(_, Buffer, Length) when byte_size(Buffer) >= Length -> {ok, binary:part(Buffer, 0, Length)};
read_body(Socket, Buffer, Length) ->
    case gen_tcp:recv(Socket, 0, 5000) of {ok, More} -> read_body(Socket, <<Buffer/binary, More/binary>>, Length); Error -> Error end.

request(Method, Target, Body) ->
    [Path | Query] = binary:split(Target, <<"?">>),
    Parts = binary:split(Path, <<"/">>, [global]),
    route(Method, Parts, Query, Body).

route(<<"GET">>, [<<>>, <<"health">>], _, _) -> {200, #{status => <<"ok">>}};
route(<<"GET">>, [<<>>, <<"books">>], Query, _) ->
    Filter = author_filter(Query),
    {200, books_store:list(Filter)};
route(<<"POST">>, [<<>>, <<"books">>], _, Body) ->
    with_book(Body, fun(Book) -> {201, books_store:create(Book)} end);
route(Method, [<<>>, <<"books">>, IdBin], _, Body) ->
    case parse_id(IdBin) of
        error -> {404, #{error => <<"Book not found">>}};
        Id -> item(Method, Id, Body)
    end;
route(_, _, _, _) -> {404, #{error => <<"Not found">>}}.

item(<<"GET">>, Id, _) -> found(books_store:get(Id));
item(<<"PUT">>, Id, Body) -> with_book(Body, fun(Book) -> found(books_store:update(Id, Book)) end);
item(<<"DELETE">>, Id, _) ->
    case books_store:delete(Id) of ok -> {200, #{message => <<"Book deleted">>}}; not_found -> found(not_found) end;
item(_, _, _) -> {405, #{error => <<"Method not allowed">>}}.
found(not_found) -> {404, #{error => <<"Book not found">>}};
found({ok, Book}) -> {200, Book}.
parse_id(Bin) -> try binary_to_integer(Bin) of N when N > 0 -> N; _ -> error catch _:_ -> error end.
author_filter([]) -> undefined;
author_filter([Query]) ->
    try proplists:get_value("author", uri_string:dissect_query(binary_to_list(Query)), undefined) of
        undefined -> undefined; Value -> unicode:characters_to_binary(Value)
    catch _:_ -> undefined end.
with_book(Body, Fun) ->
    try json:decode(Body) of
        Map when is_map(Map) ->
            Title = maps:get(<<"title">>, Map, undefined), Author = maps:get(<<"author">>, Map, undefined),
            Year = maps:get(<<"year">>, Map, null), Isbn = maps:get(<<"isbn">>, Map, null),
            case valid_string(Title) andalso valid_string(Author) andalso
                 (Year =:= null orelse is_integer(Year)) andalso
                 (Isbn =:= null orelse is_binary(Isbn)) of
                true -> Fun(#{title => Title, author => Author, year => Year, isbn => Isbn});
                false -> {400, #{error => <<"Invalid book: title and author are required; year must be an integer and isbn a string">>}}
            end;
        _ -> {400, #{error => <<"Expected a JSON object">>}}
    catch _:_ -> {400, #{error => <<"Invalid JSON">>}} end.
valid_string(Value) when is_binary(Value) -> byte_size(string:trim(Value)) > 0;
valid_string(_) -> false.
reason(200) -> "OK"; reason(201) -> "Created"; reason(400) -> "Bad Request"; reason(404) -> "Not Found"; reason(405) -> "Method Not Allowed"; reason(500) -> "Internal Server Error".
