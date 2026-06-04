%%%-------------------------------------------------------------------
%% @doc books_handler: REST endpoints for the book collection.
%%
%% Routes (see booksapp_app):
%%   POST   /books        create a book
%%   GET    /books        list books (optional ?author= filter)
%%   GET    /books/:id    fetch one book
%%   PUT    /books/:id    update a book
%%   DELETE /books/:id    delete a book
%%%-------------------------------------------------------------------
-module(books_handler).

-export([init/2]).

init(Req0, State) ->
    Method = cowboy_req:method(Req0),
    Id = cowboy_req:binding(id, Req0),
    Req = handle(Method, Id, Req0),
    {ok, Req, State}.

%%====================================================================
%% Collection routes (/books)
%%====================================================================

handle(<<"GET">>, undefined, Req) ->
    Qs = cowboy_req:parse_qs(Req),
    Books = case lists:keyfind(<<"author">>, 1, Qs) of
        {<<"author">>, Author} -> book_store:list(Author);
        false -> book_store:list()
    end,
    reply(200, Books, Req);

handle(<<"POST">>, undefined, Req0) ->
    case read_json(Req0) of
        {ok, Attrs, Req1} ->
            case book_store:create(Attrs) of
                {ok, Book} -> reply(201, Book, Req1);
                {error, Reason} -> error_reply(400, Reason, Req1)
            end;
        {error, Req1} ->
            error_reply(400, <<"invalid JSON body">>, Req1)
    end;

%%====================================================================
%% Member routes (/books/:id)
%%====================================================================

handle(<<"GET">>, IdBin, Req) ->
    with_id(IdBin, Req, fun(Id) ->
        case book_store:get(Id) of
            {ok, Book} -> reply(200, Book, Req);
            {error, not_found} -> error_reply(404, <<"book not found">>, Req)
        end
    end);

handle(<<"PUT">>, IdBin, Req0) ->
    with_id(IdBin, Req0, fun(Id) ->
        case read_json(Req0) of
            {ok, Attrs, Req1} ->
                case book_store:update(Id, Attrs) of
                    {ok, Book} -> reply(200, Book, Req1);
                    {error, not_found} -> error_reply(404, <<"book not found">>, Req1);
                    {error, Reason} -> error_reply(400, Reason, Req1)
                end;
            {error, Req1} ->
                error_reply(400, <<"invalid JSON body">>, Req1)
        end
    end);

handle(<<"DELETE">>, IdBin, Req) ->
    with_id(IdBin, Req, fun(Id) ->
        case book_store:delete(Id) of
            ok -> reply(204, no_body, Req);
            {error, not_found} -> error_reply(404, <<"book not found">>, Req)
        end
    end);

handle(_Method, _Id, Req) ->
    error_reply(405, <<"method not allowed">>, Req).

%%====================================================================
%% Helpers
%%====================================================================

%% Parse the :id binding into an integer, replying 400 if malformed.
with_id(IdBin, Req, Fun) ->
    try binary_to_integer(IdBin) of
        Id -> Fun(Id)
    catch
        error:badarg -> error_reply(400, <<"invalid id">>, Req)
    end.

%% Read and decode a JSON request body into a map.
read_json(Req0) ->
    {ok, Body, Req1} = cowboy_req:read_body(Req0),
    try json:decode(Body) of
        Map when is_map(Map) -> {ok, Map, Req1};
        _ -> {error, Req1}
    catch
        _:_ -> {error, Req1}
    end.

reply(Status, no_body, Req) ->
    cowboy_req:reply(Status, #{}, <<>>, Req);
reply(Status, Term, Req) ->
    cowboy_req:reply(Status,
        #{<<"content-type">> => <<"application/json">>},
        json:encode(Term),
        Req).

error_reply(Status, Message, Req) ->
    reply(Status, #{<<"error">> => Message}, Req).
