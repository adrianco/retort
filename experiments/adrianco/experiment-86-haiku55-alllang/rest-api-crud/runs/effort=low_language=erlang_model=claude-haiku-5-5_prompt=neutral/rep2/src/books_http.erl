%% Cowboy handlers for the /health and /books routes.
-module(books_http).

-export([init/2]).

init(Req0, health) ->
    Req = case cowboy_req:method(Req0) of
        <<"GET">> -> json_reply(200, #{status => <<"ok">>}, Req0);
        _ -> method_not_allowed(<<"GET">>, Req0)
    end,
    {ok, Req, health};
init(Req0, collection) ->
    Req = case cowboy_req:method(Req0) of
        <<"GET">> -> list_books(Req0);
        <<"POST">> -> create_book(Req0);
        _ -> method_not_allowed(<<"GET, POST">>, Req0)
    end,
    {ok, Req, collection};
init(Req0, item) ->
    Req = case parse_id(cowboy_req:binding(id, Req0)) of
        {ok, Id} -> item_request(cowboy_req:method(Req0), Id, Req0);
        error -> not_found(Req0)
    end,
    {ok, Req, item}.

list_books(Req) ->
    #{author := Author} = cowboy_req:match_qs([{author, [], undefined}], Req),
    {ok, Books} = books_store:list(Author),
    json_reply(200, Books, Req).

create_book(Req0) ->
    with_valid_body(Req0, fun(Attrs, Req) ->
        {ok, Book} = books_store:create(Attrs),
        Location = <<"/books/", (integer_to_binary(maps:get(id, Book)))/binary>>,
        json_reply(201, Book, Req, #{<<"location">> => Location})
    end).

item_request(<<"GET">>, Id, Req) ->
    case books_store:get(Id) of
        {ok, Book} -> json_reply(200, Book, Req);
        {error, not_found} -> not_found(Req)
    end;
item_request(<<"PUT">>, Id, Req0) ->
    with_valid_body(Req0, fun(Attrs, Req) ->
        case books_store:update(Id, Attrs) of
            {ok, Book} -> json_reply(200, Book, Req);
            {error, not_found} -> not_found(Req)
        end
    end);
item_request(<<"DELETE">>, Id, Req) ->
    case books_store:delete(Id) of
        ok -> cowboy_req:reply(204, #{}, <<>>, Req);
        {error, not_found} -> not_found(Req)
    end;
item_request(_, _, Req) ->
    method_not_allowed(<<"GET, PUT, DELETE">>, Req).

with_valid_body(Req0, Fun) ->
    {Body, Req} = read_body(Req0, <<>>),
    case decode(Body) of
        {ok, Params} ->
            case books_validate:validate(Params) of
                {ok, Attrs} -> Fun(Attrs, Req);
                {error, Errors} ->
                    json_reply(400, #{error => <<"validation failed">>, details => Errors}, Req)
            end;
        error ->
            json_reply(400, #{error => <<"request body must be valid JSON">>}, Req)
    end.

read_body(Req0, Acc) ->
    case cowboy_req:read_body(Req0) of
        {ok, Data, Req} -> {<<Acc/binary, Data/binary>>, Req};
        {more, Data, Req} -> read_body(Req, <<Acc/binary, Data/binary>>)
    end.

decode(Body) ->
    try json:decode(Body) of
        Value -> {ok, Value}
    catch
        _:_ -> error
    end.

parse_id(undefined) ->
    error;
parse_id(Bin) ->
    try binary_to_integer(Bin) of
        Id when Id > 0 -> {ok, Id};
        _ -> error
    catch
        error:badarg -> error
    end.

not_found(Req) ->
    json_reply(404, #{error => <<"book not found">>}, Req).

method_not_allowed(Allowed, Req) ->
    json_reply(405, #{error => <<"method not allowed">>}, Req, #{<<"allow">> => Allowed}).

json_reply(Status, Body, Req) ->
    json_reply(Status, Body, Req, #{}).

json_reply(Status, Body, Req, Headers) ->
    cowboy_req:reply(Status,
                     Headers#{<<"content-type">> => <<"application/json">>},
                     json:encode(Body),
                     Req).
