%% HTTP handler for /books and /books/:id.
-module(books_handler).
-behaviour(cowboy_handler).

-export([init/2]).

init(Req0, State) ->
    Method = cowboy_req:method(Req0),
    IdBinding = cowboy_req:binding(id, Req0),
    Req = handle(Method, IdBinding, Req0),
    {ok, Req, State}.

%%% Routing ------------------------------------------------------------------

handle(<<"GET">>, undefined, Req) ->
    Qs = cowboy_req:parse_qs(Req),
    Books = case lists:keyfind(<<"author">>, 1, Qs) of
                {_, Author} -> book_store:list_by_author(Author);
                false -> book_store:list()
            end,
    reply_json(200, Books, Req);
handle(<<"POST">>, undefined, Req0) ->
    with_valid_body(Req0, fun(Fields, Req) ->
        {ok, Book} = book_store:create(Fields),
        reply_json(201, Book, Req)
    end);
handle(<<"GET">>, IdBin, Req) ->
    with_id(IdBin, Req, fun(Id) ->
        case book_store:get(Id) of
            {ok, Book} -> reply_json(200, Book, Req);
            not_found -> not_found(Req)
        end
    end);
handle(<<"PUT">>, IdBin, Req0) ->
    with_id(IdBin, Req0, fun(Id) ->
        with_valid_body(Req0, fun(Fields, Req) ->
            case book_store:update(Id, Fields) of
                {ok, Book} -> reply_json(200, Book, Req);
                not_found -> not_found(Req)
            end
        end)
    end);
handle(<<"DELETE">>, IdBin, Req) ->
    with_id(IdBin, Req, fun(Id) ->
        case book_store:delete(Id) of
            ok -> cowboy_req:reply(204, Req);
            not_found -> not_found(Req)
        end
    end);
handle(_Method, _Id, Req) ->
    reply_json(405, #{error => <<"method not allowed">>}, Req).

%%% Request helpers ----------------------------------------------------------

with_id(IdBin, Req, Fun) ->
    try binary_to_integer(IdBin) of
        Id when Id > 0 -> Fun(Id);
        _ -> not_found(Req)
    catch
        error:badarg -> not_found(Req)
    end.

with_valid_body(Req0, Fun) ->
    {ok, Body, Req} = cowboy_req:read_body(Req0),
    case decode_json(Body) of
        {ok, Fields} when is_map(Fields) ->
            case books_validate:book(Fields) of
                {ok, Clean} -> Fun(Clean, Req);
                {error, Errors} ->
                    reply_json(400, #{errors => Errors}, Req)
            end;
        _ ->
            reply_json(400, #{errors => [<<"request body must be a JSON object">>]}, Req)
    end.

decode_json(Body) ->
    try
        {ok, json:decode(Body)}
    catch
        _:_ -> error
    end.

not_found(Req) ->
    reply_json(404, #{error => <<"book not found">>}, Req).

reply_json(Status, Term, Req) ->
    cowboy_req:reply(Status,
                     #{<<"content-type">> => <<"application/json">>},
                     json:encode(Term),
                     Req).
