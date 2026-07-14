%%% @doc Cowboy handler for the /books resource.
%%%
%%% Routes:
%%%   POST   /books        create a book
%%%   GET    /books        list books (optional ?author= filter)
%%%   GET    /books/:id    fetch one book
%%%   PUT    /books/:id    update a book
%%%   DELETE /books/:id    delete a book
-module(book_handler).

-export([init/2]).

init(Req0, State) ->
    Method = cowboy_req:method(Req0),
    Id = cowboy_req:binding(id, Req0),
    Req = handle(Method, Id, Req0),
    {ok, Req, State}.

%%% --- Collection routes (no id) ---

handle(<<"POST">>, undefined, Req0) ->
    case read_json_body(Req0) of
        {ok, Data, Req1} when is_map(Data) ->
            case validate(Data) of
                {ok, Fields} ->
                    {ok, Book} = book_store:create(Fields),
                    reply(201, Book, Req1);
                {error, Reason} ->
                    error_reply(400, Reason, Req1)
            end;
        {ok, _NotAnObject, Req1} ->
            error_reply(400, <<"request body must be a JSON object">>, Req1);
        {error, Req1} ->
            error_reply(400, <<"invalid JSON in request body">>, Req1)
    end;

handle(<<"GET">>, undefined, Req0) ->
    Books = case cowboy_req:match_qs([{author, [], undefined}], Req0) of
        #{author := undefined} -> book_store:list();
        #{author := Author} -> book_store:list_by_author(Author)
    end,
    reply(200, Books, Req0);

%%% --- Single-resource routes (with id) ---

handle(<<"GET">>, IdBin, Req0) ->
    with_id(IdBin, Req0, fun(Id) ->
        case book_store:get(Id) of
            {ok, Book} -> reply(200, Book, Req0);
            {error, not_found} -> not_found(Req0)
        end
    end);

handle(<<"PUT">>, IdBin, Req0) ->
    with_id(IdBin, Req0, fun(Id) ->
        case read_json_body(Req0) of
            {ok, Data, Req1} when is_map(Data) ->
                case validate_update(Data) of
                    {ok, Fields} ->
                        case book_store:update(Id, Fields) of
                            {ok, Book} -> reply(200, Book, Req1);
                            {error, not_found} -> not_found(Req1)
                        end;
                    {error, Reason} ->
                        error_reply(400, Reason, Req1)
                end;
            {ok, _NotAnObject, Req1} ->
                error_reply(400, <<"request body must be a JSON object">>, Req1);
            {error, Req1} ->
                error_reply(400, <<"invalid JSON in request body">>, Req1)
        end
    end);

handle(<<"DELETE">>, IdBin, Req0) ->
    with_id(IdBin, Req0, fun(Id) ->
        case book_store:delete(Id) of
            ok -> cowboy_req:reply(204, #{}, <<>>, Req0);
            {error, not_found} -> not_found(Req0)
        end
    end);

handle(_Method, _Id, Req0) ->
    error_reply(405, <<"method not allowed">>, Req0).

%%% --- Validation ---

%% On create, title and author are required and must be non-empty strings.
validate(Data) ->
    case {field(<<"title">>, Data), field(<<"author">>, Data)} of
        {{ok, Title}, {ok, Author}} ->
            {ok, optional_fields(Data, #{title => Title, author => Author})};
        {{error, R}, _} ->
            {error, R};
        {_, {error, R}} ->
            {error, R}
    end.

%% On update, fields are optional, but any provided title/author must be valid.
validate_update(Data) ->
    Acc0 = #{},
    case validate_optional(<<"title">>, title, Data, Acc0) of
        {error, R} -> {error, R};
        {ok, Acc1} ->
            case validate_optional(<<"author">>, author, Data, Acc1) of
                {error, R} -> {error, R};
                {ok, Acc2} -> {ok, optional_fields(Data, Acc2)}
            end
    end.

validate_optional(Key, MapKey, Data, Acc) ->
    case maps:is_key(Key, Data) of
        false -> {ok, Acc};
        true ->
            case field(Key, Data) of
                {ok, Value} -> {ok, Acc#{MapKey => Value}};
                {error, R} -> {error, R}
            end
    end.

%% A required/typed string field: present, a binary, and non-empty after trim.
field(Key, Data) ->
    case maps:get(Key, Data, undefined) of
        undefined ->
            {error, <<Key/binary, " is required">>};
        Value when is_binary(Value) ->
            case string:trim(Value) of
                <<>> -> {error, <<Key/binary, " must not be empty">>};
                _ -> {ok, Value}
            end;
        _ ->
            {error, <<Key/binary, " must be a string">>}
    end.

%% Copy through optional year/isbn fields when present.
optional_fields(Data, Acc0) ->
    Acc1 = case maps:get(<<"year">>, Data, undefined) of
        undefined -> Acc0;
        Year -> Acc0#{year => Year}
    end,
    case maps:get(<<"isbn">>, Data, undefined) of
        undefined -> Acc1;
        Isbn -> Acc1#{isbn => Isbn}
    end.

%%% --- Helpers ---

with_id(IdBin, Req0, Fun) ->
    case parse_id(IdBin) of
        {ok, Id} -> Fun(Id);
        error -> error_reply(400, <<"id must be an integer">>, Req0)
    end.

parse_id(IdBin) ->
    try binary_to_integer(IdBin) of
        Id -> {ok, Id}
    catch
        error:badarg -> error
    end.

read_json_body(Req0) ->
    {ok, Body, Req1} = cowboy_req:read_body(Req0),
    try json:decode(Body) of
        Data -> {ok, Data, Req1}
    catch
        _:_ -> {error, Req1}
    end.

reply(Status, Term, Req) ->
    cowboy_req:reply(Status,
        #{<<"content-type">> => <<"application/json">>},
        json:encode(Term), Req).

error_reply(Status, Message, Req) ->
    reply(Status, #{<<"error">> => Message}, Req).

not_found(Req) ->
    error_reply(404, <<"book not found">>, Req).
