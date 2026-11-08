-module(books_handler).
-export([init/2, validate/1]).

init(Req0, Route) ->
    Method = cowboy_req:method(Req0),
    try dispatch(Route, Method, Req0) of
        {Status, Body, Req} -> reply(Status, Body, Req, Route)
    catch
        throw:{http_error, Status, Message} -> reply(Status, #{error => Message}, Req0, Route)
    end.

dispatch(health, <<"GET">>, Req) -> {200, #{status => <<"ok">>}, Req};
dispatch(collection, <<"GET">>, Req) ->
    Author = proplists:get_value(<<"author">>, cowboy_req:parse_qs(Req)),
    {200, books_store:list(Author), Req};
dispatch(collection, <<"POST">>, Req0) ->
    {Book, Req} = read_book(Req0),
    {ok, Created} = books_store:create(Book), {201, Created, Req};
dispatch(item, Method, Req0) when Method =:= <<"GET">>; Method =:= <<"PUT">>; Method =:= <<"DELETE">> ->
    Id = parse_id(cowboy_req:binding(id, Req0)),
    case Method of
        <<"GET">> -> result(books_store:get(Id), Req0);
        <<"PUT">> ->
            {Book, Req} = read_book(Req0), result(books_store:update(Id, Book), Req);
        <<"DELETE">> ->
            case books_store:delete(Id) of
                ok -> {200, #{deleted => true}, Req0};
                not_found -> {404, #{error => <<"Book not found">>}, Req0}
            end
    end;
dispatch(_, _, Req) -> {405, #{error => <<"Method not allowed">>}, Req}.

result({ok, Book}, Req) -> {200, Book, Req};
result(not_found, Req) -> {404, #{error => <<"Book not found">>}, Req}.
parse_id(Bin) ->
    try binary_to_integer(Bin) of
        I when I > 0 -> I;
        _ -> throw({http_error, 400, <<"Invalid book ID">>})
    catch error:badarg -> throw({http_error, 400, <<"Invalid book ID">>}) end.
read_book(Req0) ->
    {Data, Req} = read_body(Req0, <<>>),
    Decoded = try jsx:decode(Data, [return_maps]) catch _:_ -> throw({http_error, 400, <<"Invalid JSON">>}) end,
    case validate(Decoded) of
        {ok, Book} -> {Book, Req};
        {error, Message} -> throw({http_error, 400, Message})
    end.
read_body(Req0, Acc) ->
    case cowboy_req:read_body(Req0, #{length => 65536}) of
        {ok, Data, Req} when byte_size(Acc) + byte_size(Data) =< 65536 -> {<<Acc/binary, Data/binary>>, Req};
        {more, Data, Req} when byte_size(Acc) + byte_size(Data) =< 65536 -> read_body(Req, <<Acc/binary, Data/binary>>);
        _ -> throw({http_error, 413, <<"Request body too large">>})
    end.
validate(Map) when is_map(Map) ->
    Title = maps:get(<<"title">>, Map, undefined),
    Author = maps:get(<<"author">>, Map, undefined),
    Year = maps:get(<<"year">>, Map, null),
    Isbn = maps:get(<<"isbn">>, Map, null),
    case nonempty(Title) andalso nonempty(Author) andalso
         (Year =:= null orelse (is_integer(Year) andalso Year > 0)) andalso
         (Isbn =:= null orelse is_binary(Isbn)) of
        true -> {ok, #{<<"title">> => Title, <<"author">> => Author, <<"year">> => Year, <<"isbn">> => Isbn}};
        false -> {error, <<"title and author must be non-empty strings; year must be a positive integer and isbn a string">>}
    end;
validate(_) -> {error, <<"Expected a JSON object">>}.
nonempty(Value) when is_binary(Value) ->
    try string:trim(Value) =/= <<>> catch _:_ -> false end;
nonempty(_) -> false.
reply(Status, Body, Req, Route) ->
    Allow = case Route of health -> <<"GET">>; collection -> <<"GET, POST">>; item -> <<"GET, PUT, DELETE">> end,
    Headers = #{<<"content-type">> => <<"application/json; charset=utf-8">>, <<"allow">> => Allow},
    {ok, cowboy_req:reply(Status, Headers, jsx:encode(Body), Req), Route}.
