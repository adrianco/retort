%% Handles /books (collection) and /books/:id (item).
-module(book_api_books_handler).
-behaviour(cowboy_handler).

-export([init/2]).
-export([reply/3, method_not_allowed/2, validate/1]).

-define(MAX_BODY, 1048576).

init(Req0, collection = State) ->
    Req =
        case cowboy_req:method(Req0) of
            <<"GET">> -> list_books(Req0);
            <<"POST">> -> create_book(Req0);
            _ -> method_not_allowed(<<"GET, POST">>, Req0)
        end,
    {ok, Req, State};
init(Req0, item = State) ->
    Req =
        case parse_id(cowboy_req:binding(id, Req0)) of
            {ok, Id} ->
                case cowboy_req:method(Req0) of
                    <<"GET">> -> get_book(Id, Req0);
                    <<"PUT">> -> update_book(Id, Req0);
                    <<"DELETE">> -> delete_book(Id, Req0);
                    _ -> method_not_allowed(<<"GET, PUT, DELETE">>, Req0)
                end;
            error ->
                error_reply(400, <<"book id must be a positive integer">>, Req0)
        end,
    {ok, Req, State}.

%% --- actions ---------------------------------------------------------------

list_books(Req) ->
    Author =
        case lists:keyfind(<<"author">>, 1, cowboy_req:parse_qs(Req)) of
            {_, Value} when is_binary(Value) -> Value;
            _ -> undefined
        end,
    reply(200, book_store:list(Author), Req).

create_book(Req0) ->
    case read_book(Req0) of
        {ok, Fields, Req} ->
            Book = book_store:create(Fields),
            Location = [<<"/books/">>, integer_to_binary(maps:get(id, Book))],
            reply(201, Book, cowboy_req:set_resp_header(<<"location">>, Location, Req));
        {error, Status, Body, Req} ->
            reply(Status, Body, Req)
    end.

get_book(Id, Req) ->
    case book_store:get(Id) of
        {ok, Book} -> reply(200, Book, Req);
        not_found -> not_found(Req)
    end.

update_book(Id, Req0) ->
    case read_book(Req0) of
        {ok, Fields, Req} ->
            case book_store:update(Id, Fields) of
                {ok, Book} -> reply(200, Book, Req);
                not_found -> not_found(Req)
            end;
        {error, Status, Body, Req} ->
            reply(Status, Body, Req)
    end.

delete_book(Id, Req) ->
    case book_store:delete(Id) of
        ok -> cowboy_req:reply(204, Req);
        not_found -> not_found(Req)
    end.

%% --- request parsing and validation ----------------------------------------

read_book(Req0) ->
    case cowboy_req:read_body(Req0, #{length => ?MAX_BODY}) of
        {ok, Body, Req} ->
            case decode(Body) of
                {ok, Json} when is_map(Json) ->
                    case validate(Json) of
                        {ok, Fields} ->
                            {ok, Fields, Req};
                        {error, Errors} ->
                            Msg = #{error => <<"validation failed">>, details => Errors},
                            {error, 422, Msg, Req}
                    end;
                {ok, _} ->
                    {error, 400, #{error => <<"request body must be a JSON object">>}, Req};
                error ->
                    {error, 400, #{error => <<"request body is not valid JSON">>}, Req}
            end;
        {more, _, Req} ->
            {error, 413, #{error => <<"request body too large">>}, Req}
    end.

decode(Body) ->
    try
        {ok, json:decode(Body)}
    catch
        error:_ -> error
    end.

%% Checks a decoded JSON object and returns the normalised book fields, or a
%% map of field name => problem description.
-spec validate(map()) -> {ok, map()} | {error, map()}.
validate(Json) ->
    Checks = [
        {title, required_string(<<"title">>, Json)},
        {author, required_string(<<"author">>, Json)},
        {year, optional_year(Json)},
        {isbn, optional_string(<<"isbn">>, Json)}
    ],
    case [{K, Msg} || {K, {error, Msg}} <- Checks] of
        [] -> {ok, maps:from_list([{K, V} || {K, {ok, V}} <- Checks])};
        Errors -> {error, maps:from_list(Errors)}
    end.

required_string(Key, Json) ->
    case maps:get(Key, Json, null) of
        null ->
            {error, <<"is required">>};
        Value when is_binary(Value) ->
            case string:trim(Value) of
                <<>> -> {error, <<"must not be blank">>};
                Trimmed -> {ok, Trimmed}
            end;
        _ ->
            {error, <<"must be a string">>}
    end.

optional_string(Key, Json) ->
    case maps:get(Key, Json, null) of
        null -> {ok, null};
        Value when is_binary(Value) -> {ok, Value};
        _ -> {error, <<"must be a string">>}
    end.

optional_year(Json) ->
    case maps:get(<<"year">>, Json, null) of
        null -> {ok, null};
        Year when is_integer(Year) -> {ok, Year};
        _ -> {error, <<"must be an integer">>}
    end.

parse_id(Bin) ->
    try binary_to_integer(Bin) of
        Id when Id > 0 -> {ok, Id};
        _ -> error
    catch
        error:badarg -> error
    end.

%% --- responses -------------------------------------------------------------

reply(Status, Body, Req) ->
    cowboy_req:reply(
        Status,
        #{<<"content-type">> => <<"application/json">>},
        json:encode(Body),
        Req
    ).

not_found(Req) ->
    error_reply(404, <<"book not found">>, Req).

method_not_allowed(Allow, Req) ->
    error_reply(405, <<"method not allowed">>, cowboy_req:set_resp_header(<<"allow">>, Allow, Req)).

error_reply(Status, Message, Req) ->
    reply(Status, #{error => Message}, Req).
