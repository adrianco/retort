%% HTTP handler for /books (collection) and /books/:id (item).
-module(books_handler).

-export([init/2, reply/3, validate/1]).

-define(MAX_BODY, 1048576).
%% Largest value SQLite's INTEGER column can hold.
-define(MAX_INT, 9223372036854775807).

init(Req0, Kind) ->
    Req = try
              handle(Kind, cowboy_req:method(Req0), Req0)
          catch
              Class:Reason:Stack ->
                  logger:error("request failed: ~p:~p ~p", [Class, Reason, Stack]),
                  reply(500, #{error => <<"internal server error">>}, Req0)
          end,
    {ok, Req, Kind}.

handle(collection, <<"GET">>, Req) ->
    Author = case lists:keyfind(<<"author">>, 1, cowboy_req:parse_qs(Req)) of
                 {_, A} when is_binary(A) -> A;
                 _ -> undefined
             end,
    reply(200, books_db:list(Author), Req);
handle(collection, <<"POST">>, Req0) ->
    with_book(Req0, fun(Book, Req) ->
        {ok, Created} = books_db:create(Book),
        Location = [<<"/books/">>, integer_to_binary(maps:get(id, Created))],
        reply(201, Created, cowboy_req:set_resp_header(<<"location">>, Location, Req))
    end);
handle(collection, _, Req) ->
    method_not_allowed(<<"GET, POST">>, Req);
handle(item, Method, Req) ->
    case parse_id(cowboy_req:binding(id, Req)) of
        {ok, Id} -> handle_item(Method, Id, Req);
        error -> not_found(Req)
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
    method_not_allowed(<<"GET, PUT, DELETE">>, Req).

%% Reads, decodes and validates the request body, then calls Fun with the book.
with_book(Req0, Fun) ->
    case read_body(Req0, <<>>) of
        {ok, Body, Req} ->
            case decode(Body) of
                {ok, Json} ->
                    case validate(Json) of
                        {ok, Book} ->
                            Fun(Book, Req);
                        {error, Errors} ->
                            reply(400, #{error => <<"validation failed">>,
                                         details => Errors}, Req)
                    end;
                error ->
                    reply(400, #{error => <<"invalid JSON body">>}, Req)
            end;
        {too_large, Req} ->
            reply(413, #{error => <<"request body too large">>}, Req)
    end.

read_body(Req0, Acc) when byte_size(Acc) > ?MAX_BODY ->
    {too_large, Req0};
read_body(Req0, Acc) ->
    case cowboy_req:read_body(Req0) of
        {ok, Data, Req} when byte_size(Acc) + byte_size(Data) > ?MAX_BODY -> {too_large, Req};
        {ok, Data, Req} -> {ok, <<Acc/binary, Data/binary>>, Req};
        {more, Data, Req} -> read_body(Req, <<Acc/binary, Data/binary>>)
    end.

decode(Body) ->
    try json:decode(Body) of
        Json -> {ok, Json}
    catch
        error:_ -> error
    end.

%% Validates a decoded JSON value: title and author are required non-empty
%% strings, year is an optional integer, isbn an optional string.
-spec validate(term()) -> {ok, map()} | {error, [binary()]}.
validate(Json) when is_map(Json) ->
    Checks = [required_string(<<"title">>, Json),
              required_string(<<"author">>, Json),
              optional(<<"year">>, Json,
                       fun(V) -> is_integer(V) andalso abs(V) =< ?MAX_INT end,
                       <<"year must be an integer">>),
              optional(<<"isbn">>, Json, fun is_binary/1, <<"isbn must be a string">>)],
    case [E || {error, E} <- Checks] of
        [] ->
            [Title, Author, Year, Isbn] = [V || {ok, V} <- Checks],
            {ok, #{title => Title, author => Author, year => Year, isbn => Isbn}};
        Errors ->
            {error, Errors}
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
        null ->
            {error, <<Key/binary, " is required">>};
        _ ->
            {error, <<Key/binary, " must be a string">>}
    end.

optional(Key, Json, Pred, Message) ->
    case maps:get(Key, Json, null) of
        null -> {ok, null};
        V ->
            case Pred(V) of
                true -> {ok, V};
                false -> {error, Message}
            end
    end.

parse_id(Bin) ->
    try binary_to_integer(Bin) of
        Id when Id > 0, Id =< ?MAX_INT -> {ok, Id};
        _ -> error
    catch
        error:badarg -> error
    end.

not_found(Req) ->
    reply(404, #{error => <<"book not found">>}, Req).

method_not_allowed(Allow, Req) ->
    reply(405, #{error => <<"method not allowed">>},
          cowboy_req:set_resp_header(<<"allow">>, Allow, Req)).

reply(Status, Term, Req) ->
    cowboy_req:reply(Status, #{<<"content-type">> => <<"application/json">>},
                     json:encode(Term), Req).
