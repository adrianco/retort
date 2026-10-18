%% /books: list (GET, optional ?author=) and create (POST).
-module(books_collection_handler).
-behaviour(cowboy_handler).

-export([init/2]).

init(Req0, State) ->
    Req = case cowboy_req:method(Req0) of
              <<"GET">> -> list(Req0);
              <<"POST">> -> create(Req0);
              _ -> method_not_allowed(Req0)
          end,
    {ok, Req, State}.

list(Req) ->
    Books = books_db:list(author_filter(Req)),
    books_http:reply_json(200, [books_http:book_to_json(B) || B <- Books], Req).

create(Req0) ->
    case books_http:read_json_body(Req0) of
        {error, invalid_json, Req} ->
            books_http:reply_error(400, <<"request body must be valid JSON">>, Req);
        {ok, Body, Req1} ->
            case books_validate:validate(Body) of
                {error, Errors} ->
                    books_http:reply_json(400, #{<<"error">> => <<"validation failed">>,
                                                 <<"details">> => Errors}, Req1);
                {ok, Attrs} ->
                    Book = books_db:insert(Attrs),
                    Id = integer_to_binary(maps:get(id, Book)),
                    Req2 = cowboy_req:set_resp_header(<<"location">>, <<"/books/", Id/binary>>, Req1),
                    books_http:reply_json(201, books_http:book_to_json(Book), Req2)
            end
    end.

author_filter(Req) ->
    case lists:keyfind(<<"author">>, 1, cowboy_req:parse_qs(Req)) of
        {<<"author">>, Author} -> Author;
        false -> undefined
    end.

method_not_allowed(Req0) ->
    Req = cowboy_req:set_resp_header(<<"allow">>, <<"GET, POST">>, Req0),
    books_http:reply_error(405, <<"method not allowed">>, Req).
