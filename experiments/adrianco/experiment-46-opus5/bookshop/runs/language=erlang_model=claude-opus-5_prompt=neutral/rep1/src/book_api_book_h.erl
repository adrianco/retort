%%%-------------------------------------------------------------------
%%% @doc Single-resource endpoint: `GET', `PUT' and `DELETE' on
%%% `/books/{id}'.
%%%
%%% `PUT' has replace semantics — `title' and `author' are required just
%%% as they are on create, and omitting `year' or `isbn' clears them.
%%% @end
%%%-------------------------------------------------------------------
-module(book_api_book_h).

-behaviour(cowboy_handler).

-export([init/2]).

-define(ALLOWED, [<<"GET">>, <<"HEAD">>, <<"PUT">>, <<"DELETE">>]).

init(Req0, State) ->
    Req = book_api_http:handle(fun() -> route(Req0) end, Req0),
    {ok, Req, State}.

route(Req) ->
    case book_api_http:parse_id(cowboy_req:binding(id, Req)) of
        error -> not_found(cowboy_req:binding(id, Req), Req);
        {ok, Id} -> dispatch(cowboy_req:method(Req), Id, Req)
    end.

dispatch(Method, Id, Req) when Method =:= <<"GET">>; Method =:= <<"HEAD">> ->
    show(Id, Req);
dispatch(<<"PUT">>, Id, Req) ->
    update(Id, Req);
dispatch(<<"DELETE">>, Id, Req) ->
    delete(Id, Req);
dispatch(_Other, _Id, Req) ->
    book_api_http:method_not_allowed(?ALLOWED, Req).

%%%===================================================================
%%% Actions
%%%===================================================================

show(Id, Req) ->
    case book_store:get(Id) of
        {ok, Book} -> book_api_http:json(200, book:to_map(Book), Req);
        {error, not_found} -> not_found(Id, Req)
    end.

update(Id, Req0) ->
    case book_api_http:read_json_body(Req0) of
        {error, Req} ->
            Req;
        {ok, Body, Req} ->
            case book:validate(Body) of
                {error, Errors} ->
                    book_api_http:error(400, <<"validation_failed">>,
                                        <<"The book could not be updated">>,
                                        Errors, Req);
                {ok, Attrs} ->
                    case book_store:update(Id, Attrs) of
                        {ok, Book} -> book_api_http:json(200, book:to_map(Book), Req);
                        {error, not_found} -> not_found(Id, Req)
                    end
            end
    end.

delete(Id, Req) ->
    case book_store:delete(Id) of
        ok -> cowboy_req:reply(204, #{}, <<>>, Req);
        {error, not_found} -> not_found(Id, Req)
    end.

not_found(Id, Req) ->
    book_api_http:error(404, <<"not_found">>,
                        ["Book ", to_text(Id), " does not exist"], Req).

to_text(Id) when is_integer(Id) -> integer_to_binary(Id);
to_text(Id) when is_binary(Id) -> Id.
