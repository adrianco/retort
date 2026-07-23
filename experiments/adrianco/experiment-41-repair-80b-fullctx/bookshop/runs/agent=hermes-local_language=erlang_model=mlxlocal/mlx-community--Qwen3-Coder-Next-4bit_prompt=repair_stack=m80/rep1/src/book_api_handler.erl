-module(book_api_handler).

-export([init/2]).

init(Req0, Opts) ->
    Method = cowboy_req:method(Req0),
    Path = cowboy_req:path(Req0),
    
    {Req, Response} = case cowboy_req:match_params(Req0) of
        #{id := Id} ->
            handle_book_request(Method, Id, Req0);
        _ ->
            handle_books_collection_request(Method, Req0)
    end,
    {ok, Req, Response}.

handle_books_collection_request(<<"POST">>, Req) ->
    {ok, Body, Req1} = cowboy_req:read_body(Req),
    case jiffy:decode(Body) of
        {error, Reason} ->
            {ok, Req2} = cowboy_req:reply(400, #{<<"content-type">> => <<"application/json">>}, 
                jiffy:encode(#{error => <<"invalid_json">>}), Req),
            {Req2, undefined};
        Decoded when is_map(Decoded) ->
            case book_api_db:create_book(Decoded) of
                {ok, Book} ->
                    {ok, Req2} = cowboy_req:reply(201, 
                        #{<<"content-type">> => <<"application/json">>}, 
                        jiffy:encode(Book), Req),
                    {Req2, undefined};
                {error, Reason} ->
                    {ok, Req2} = cowboy_req:reply(400, #{<<"content-type">> => <<"application/json">>}, 
                        jiffy:encode(#{error => Reason}), Req),
                    {Req2, undefined}
            end
    end;

handle_books_collection_request(<<"GET">>, Req) ->
    Author = case cowboy_req:query_param(<<"author">>, Req) of
        undefined -> undefined;
        AuthorVal -> binary_to_list(AuthorVal)
    end,
    
    case Author of
        undefined ->
            case book_api_db:get_all_books() of
                {ok, Books} ->
                    {ok, Req2} = cowboy_req:reply(200, 
                        #{<<"content-type">> => <<"application/json">>}, 
                        jiffy:encode(#{books => Books}), Req),
                    {Req2, undefined};
                Error ->
                    {ok, Req2} = cowboy_req:reply(500, #{<<"content-type">> => <<"application/json">>}, 
                        jiffy:encode(#{error => atom_to_list(Error)}), Req),
                    {Req2, undefined}
            end;
        AuthorName ->
            case book_api_db:get_all_books() of
                {ok, AllBooks} ->
                    Filtered = lists:filter(
                        fun(Book) -> maps:get(author, Book) =:= AuthorName end,
                        AllBooks
                    ),
                    {ok, Req2} = cowboy_req:reply(200, 
                        #{<<"content-type">> => <<"application/json">>}, 
                        jiffy:encode(#{books => Filtered}), Req),
                    {Req2, undefined}
            end
    end;

handle_books_collection_request(_, Req) ->
    {ok, Req2} = cowboy_req:reply(405, #{<<"content-type">> => <<"application/json">>}, 
        jiffy:encode(#{error => <<"method_not_allowed">>}), Req),
    {Req2, undefined}.

handle_book_request(<<"GET">>, Id, Req) ->
    BookId = list_to_integer(binary_to_list(Id)),
    case book_api_db:get_book_by_id(BookId) of
        {ok, Book} ->
            {ok, Req2} = cowboy_req:reply(200, 
                #{<<"content-type">> => <<"application/json">>}, 
                jiffy:encode(Book), Req),
            {Req2, undefined};
        {error, not_found} ->
            {ok, Req2} = cowboy_req:reply(404, #{<<"content-type">> => <<"application/json">>}, 
                jiffy:encode(#{error => <<"not_found">>}), Req),
            {Req2, undefined}
    end;

handle_book_request(<<"PUT">>, Id, Req) ->
    BookId = list_to_integer(binary_to_list(Id)),
    {ok, Body, Req1} = cowboy_req:read_body(Req),
    case jiffy:decode(Body) of
        {error, Reason} ->
            {ok, Req2} = cowboy_req:reply(400, #{<<"content-type">> => <<"application/json">>}, 
                jiffy:encode(#{error => <<"invalid_json">>}), Req),
            {Req2, undefined};
        Decoded when is_map(Decoded) ->
            case book_api_db:update_book(BookId, Decoded) of
                {ok, Book} ->
                    {ok, Req2} = cowboy_req:reply(200, 
                        #{<<"content-type">> => <<"application/json">>}, 
                        jiffy:encode(Book), Req),
                    {Req2, undefined};
                {error, not_found} ->
                    {ok, Req2} = cowboy_req:reply(404, #{<<"content-type">> => <<"application/json">>}, 
                        jiffy:encode(#{error => <<"not_found">>}), Req),
                    {Req2, undefined};
                {error, Reason1} ->
                    {ok, Req2} = cowboy_req:reply(400, #{<<"content-type">> => <<"application/json">>}, 
                        jiffy:encode(#{error => Reason1}), Req),
                    {Req2, undefined}
            end
    end;

handle_book_request(<<"DELETE">>, Id, Req) ->
    BookId = list_to_integer(binary_to_list(Id)),
    case book_api_db:delete_book(BookId) of
        ok ->
            {ok, Req2} = cowboy_req:reply(204, #{}, <<>>, Req),
            {Req2, undefined};
        {error, not_found} ->
            {ok, Req2} = cowboy_req:reply(404, #{<<"content-type">> => <<"application/json">>}, 
                jiffy:encode(#{error => <<"not_found">>}), Req),
            {Req2, undefined}
    end;

handle_book_request(_, _Id, Req) ->
    {ok, Req2} = cowboy_req:reply(405, #{<<"content-type">> => <<"application/json">>}, 
        jiffy:encode(#{error => <<"method_not_allowed">>}), Req),
    {Req2, undefined}.
