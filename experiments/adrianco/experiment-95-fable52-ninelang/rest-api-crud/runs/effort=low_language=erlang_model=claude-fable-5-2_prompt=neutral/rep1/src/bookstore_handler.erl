%% @doc Cowboy handler for all HTTP endpoints.
-module(bookstore_handler).
-behaviour(cowboy_handler).

-export([init/2]).
-export([validate/1]).

-define(MAX_BODY, 1048576).

init(Req0, Kind) ->
    Method = cowboy_req:method(Req0),
    Req = try
        handle(Kind, Method, Req0)
    catch
        throw:{reply, Status, Body} -> reply(Status, Body, Req0)
    end,
    {ok, Req, Kind}.

%%% routes

handle(health, <<"GET">>, Req) ->
    reply(200, #{status => <<"ok">>}, Req);
handle(health, _, Req) ->
    not_allowed(<<"GET">>, Req);

handle(collection, <<"GET">>, Req) ->
    Author = proplists:get_value(<<"author">>, cowboy_req:parse_qs(Req), undefined),
    Filter = case Author of
        true -> <<>>;          % "?author" with no value
        _ -> Author
    end,
    {ok, Books} = bookstore_db:list(Filter),
    reply(200, Books, Req);
handle(collection, <<"POST">>, Req0) ->
    {Book, Req} = read_book(Req0),
    {ok, Created} = bookstore_db:create(Book),
    Location = [<<"/books/">>, integer_to_binary(maps:get(id, Created))],
    reply(201, Created, cowboy_req:set_resp_header(<<"location">>, Location, Req));
handle(collection, _, Req) ->
    not_allowed(<<"GET, POST">>, Req);

handle(item, <<"GET">>, Req) ->
    found(bookstore_db:get(id(Req)), Req);
handle(item, <<"PUT">>, Req0) ->
    Id = id(Req0),
    {Book, Req} = read_book(Req0),
    found(bookstore_db:update(Id, Book), Req);
handle(item, <<"DELETE">>, Req) ->
    case bookstore_db:delete(id(Req)) of
        ok -> cowboy_req:reply(204, Req);
        not_found -> not_found(Req)
    end;
handle(item, _, Req) ->
    not_allowed(<<"GET, PUT, DELETE">>, Req).

%%% helpers

found({ok, Book}, Req) -> reply(200, Book, Req);
found(not_found, Req) -> not_found(Req).

not_found(Req) ->
    reply(404, #{error => <<"book not found">>}, Req).

not_allowed(Allow, Req) ->
    reply(405, #{error => <<"method not allowed">>},
          cowboy_req:set_resp_header(<<"allow">>, Allow, Req)).

id(Req) ->
    Bin = cowboy_req:binding(id, Req),
    try binary_to_integer(Bin) of
        Id when Id > 0, Id < 1 bsl 63 -> Id;
        _ -> throw({reply, 404, #{error => <<"book not found">>}})
    catch
        error:badarg -> throw({reply, 404, #{error => <<"book not found">>}})
    end.

read_book(Req0) ->
    case cowboy_req:read_body(Req0, #{length => ?MAX_BODY}) of
        {ok, Body, Req} ->
            Json = try json:decode(Body)
                   catch _:_ -> throw({reply, 400, #{error => <<"invalid JSON body">>}})
                   end,
            case validate(Json) of
                {ok, Book} -> {Book, Req};
                {error, Errors} ->
                    throw({reply, 400, #{error => <<"validation failed">>,
                                         details => Errors}})
            end;
        {more, _, _} ->
            throw({reply, 413, #{error => <<"request body too large">>}})
    end.

%% @doc Validate a decoded JSON value as a book.
-spec validate(term()) -> {ok, map()} | {error, [binary()]}.
validate(Json) when is_map(Json) ->
    Checks = [
        {title, required_string(<<"title">>, Json)},
        {author, required_string(<<"author">>, Json)},
        {year, optional(<<"year">>, Json, fun erlang:is_integer/1, <<"year must be an integer">>)},
        {isbn, optional(<<"isbn">>, Json, fun erlang:is_binary/1, <<"isbn must be a string">>)}
    ],
    case [E || {_, {error, E}} <- Checks] of
        [] -> {ok, #{K => V || {K, {ok, V}} <- Checks}};
        Errors -> {error, Errors}
    end;
validate(_) ->
    {error, [<<"body must be a JSON object">>]}.

required_string(Key, Json) ->
    case maps:get(Key, Json, null) of
        V when is_binary(V) ->
            case string:trim(V) of
                <<>> -> {error, <<Key/binary, " is required">>};
                _ -> {ok, V}
            end;
        null -> {error, <<Key/binary, " is required">>};
        _ -> {error, <<Key/binary, " must be a string">>}
    end.

optional(Key, Json, Pred, Msg) ->
    case maps:get(Key, Json, null) of
        null -> {ok, null};
        V -> case Pred(V) of
                 true -> {ok, V};
                 false -> {error, Msg}
             end
    end.

reply(Status, Body, Req) ->
    cowboy_req:reply(Status,
                     #{<<"content-type">> => <<"application/json">>},
                     json:encode(Body), Req).
