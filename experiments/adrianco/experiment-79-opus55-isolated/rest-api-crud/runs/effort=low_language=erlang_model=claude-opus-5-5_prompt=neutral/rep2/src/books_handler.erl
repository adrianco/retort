-module(books_handler).
-behaviour(cowboy_handler).

-export([init/2]).
%% Exported for unit tests.
-export([validate/1]).

init(Req0, Kind) ->
    Method = cowboy_req:method(Req0),
    Req =
        try
            handle(Kind, Method, Req0)
        catch
            Class:Reason:Stack ->
                logger:error("request failed: ~p:~p~n~p", [Class, Reason, Stack]),
                reply(500, #{error => <<"internal server error">>}, Req0)
        end,
    {ok, Req, Kind}.

handle(health, <<"GET">>, Req) ->
    reply(200, #{status => <<"ok">>}, Req);
handle(health, _, Req) ->
    not_allowed(<<"GET">>, Req);
handle(collection, <<"GET">>, Req) ->
    Author =
        case lists:keyfind(<<"author">>, 1, cowboy_req:parse_qs(Req)) of
            {_, A} when is_binary(A) -> A;
            _ -> undefined
        end,
    {ok, Books} = books_db:list(Author),
    reply(200, Books, Req);
handle(collection, <<"POST">>, Req0) ->
    with_book(Req0, fun(Book, Req) ->
        {ok, Created} = books_db:create(Book),
        Location = [<<"/books/">>, integer_to_binary(maps:get(id, Created))],
        reply(201, Created, cowboy_req:set_resp_header(<<"location">>, Location, Req))
    end);
handle(collection, _, Req) ->
    not_allowed(<<"GET, POST">>, Req);
handle(item, Method, Req) ->
    case parse_id(cowboy_req:binding(id, Req)) of
        {ok, Id} -> handle_item(Method, Id, Req);
        error -> reply(400, #{error => <<"id must be a positive integer">>}, Req)
    end.

handle_item(<<"GET">>, Id, Req) ->
    case books_db:get(Id) of
        {ok, Book} -> reply(200, Book, Req);
        not_found -> not_found(Req)
    end;
handle_item(<<"PUT">>, Id, Req0) ->
    with_book(Req0, fun(Book, Req) ->
        case books_db:update(Id, Book) of
            {ok, Updated} -> reply(200, Updated, Req);
            not_found -> not_found(Req)
        end
    end);
handle_item(<<"DELETE">>, Id, Req) ->
    case books_db:delete(Id) of
        ok -> cowboy_req:reply(204, Req);
        not_found -> not_found(Req)
    end;
handle_item(_, _Id, Req) ->
    not_allowed(<<"GET, PUT, DELETE">>, Req).

%% Reads, decodes and validates the request body, replying 400/422 on failure.
with_book(Req0, Fun) ->
    case read_body(Req0, <<>>) of
        {ok, Body, Req} ->
            case decode(Body) of
                {ok, Json} ->
                    case validate(Json) of
                        {ok, Book} ->
                            Fun(Book, Req);
                        {error, Errors} ->
                            reply(
                                422,
                                #{error => <<"validation failed">>, details => Errors},
                                Req
                            )
                    end;
                error ->
                    reply(400, #{error => <<"request body must be valid JSON">>}, Req)
            end;
        {too_large, Req} ->
            reply(413, #{error => <<"request body too large">>}, Req)
    end.

-define(MAX_BODY, 1048576).

read_body(Req0, Acc) ->
    case cowboy_req:read_body(Req0) of
        {_, Data, Req} when byte_size(Acc) + byte_size(Data) > ?MAX_BODY ->
            {too_large, Req};
        {ok, Data, Req} ->
            {ok, <<Acc/binary, Data/binary>>, Req};
        {more, Data, Req} ->
            read_body(Req, <<Acc/binary, Data/binary>>)
    end.

decode(Body) ->
    try
        {ok, json:decode(Body)}
    catch
        _:_ -> error
    end.

%% Validates a decoded JSON value, returning a normalised book map or a
%% map of field => message.
-spec validate(term()) -> {ok, map()} | {error, map()}.
validate(Json) when is_map(Json) ->
    Checks = [
        {title, required_string(<<"title">>, Json)},
        {author, required_string(<<"author">>, Json)},
        {year, optional_integer(<<"year">>, Json)},
        {isbn, optional_string(<<"isbn">>, Json)}
    ],
    Errors = maps:from_list([{K, Msg} || {K, {error, Msg}} <- Checks]),
    case map_size(Errors) of
        0 -> {ok, maps:from_list([{K, V} || {K, {ok, V}} <- Checks])};
        _ -> {error, Errors}
    end;
validate(_) ->
    {error, #{body => <<"must be a JSON object">>}}.

required_string(Key, Json) ->
    case maps:get(Key, Json, null) of
        V when is_binary(V) ->
            case string:trim(V) of
                <<>> -> {error, <<"is required">>};
                Trimmed -> {ok, Trimmed}
            end;
        null ->
            {error, <<"is required">>};
        _ ->
            {error, <<"must be a string">>}
    end.

optional_string(Key, Json) ->
    case maps:get(Key, Json, null) of
        V when is_binary(V); V =:= null -> {ok, V};
        _ -> {error, <<"must be a string">>}
    end.

optional_integer(Key, Json) ->
    case maps:get(Key, Json, null) of
        V when is_integer(V); V =:= null -> {ok, V};
        _ -> {error, <<"must be an integer">>}
    end.

parse_id(Bin) ->
    try binary_to_integer(Bin) of
        Id when Id > 0 -> {ok, Id};
        _ -> error
    catch
        error:badarg -> error
    end.

not_found(Req) ->
    reply(404, #{error => <<"book not found">>}, Req).

not_allowed(Allow, Req) ->
    reply(
        405,
        #{error => <<"method not allowed">>},
        cowboy_req:set_resp_header(<<"allow">>, Allow, Req)
    ).

reply(Status, Body, Req) ->
    cowboy_req:reply(
        Status,
        #{<<"content-type">> => <<"application/json">>},
        json:encode(Body),
        Req
    ).
