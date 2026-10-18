%% /books/{id}: fetch (GET), replace (PUT) and delete (DELETE).
-module(books_item_handler).
-behaviour(cowboy_handler).

-export([init/2]).

init(Req0, State) ->
    Req = case books_http:parse_id(cowboy_req:binding(id, Req0)) of
              error -> not_found(Req0);
              {ok, Id} -> dispatch(cowboy_req:method(Req0), Id, Req0)
          end,
    {ok, Req, State}.

dispatch(<<"GET">>, Id, Req) ->
    case books_db:get(Id) of
        {ok, Book} -> books_http:reply_json(200, books_http:book_to_json(Book), Req);
        not_found -> not_found(Req)
    end;
dispatch(<<"PUT">>, Id, Req0) ->
    case books_http:read_json_body(Req0) of
        {error, invalid_json, Req} ->
            books_http:reply_error(400, <<"request body must be valid JSON">>, Req);
        {ok, Body, Req1} ->
            case books_validate:validate(Body) of
                {error, Errors} ->
                    books_http:reply_json(400, #{<<"error">> => <<"validation failed">>,
                                                 <<"details">> => Errors}, Req1);
                {ok, Attrs} ->
                    case books_db:update(Id, Attrs) of
                        {ok, Book} -> books_http:reply_json(200, books_http:book_to_json(Book), Req1);
                        not_found -> not_found(Req1)
                    end
            end
    end;
dispatch(<<"DELETE">>, Id, Req) ->
    case books_db:delete(Id) of
        ok -> cowboy_req:reply(204, Req);
        not_found -> not_found(Req)
    end;
dispatch(_, _Id, Req0) ->
    Req = cowboy_req:set_resp_header(<<"allow">>, <<"GET, PUT, DELETE">>, Req0),
    books_http:reply_error(405, <<"method not allowed">>, Req).

not_found(Req) ->
    books_http:reply_error(404, <<"book not found">>, Req).
