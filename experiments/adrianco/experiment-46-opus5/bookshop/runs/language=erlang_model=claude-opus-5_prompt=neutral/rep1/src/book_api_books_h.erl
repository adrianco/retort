%%%-------------------------------------------------------------------
%%% @doc Collection endpoint.
%%%
%%% <ul>
%%%   <li>`GET /books' — list every book, optionally narrowed with
%%%       `?author=' (case-insensitive exact match).</li>
%%%   <li>`POST /books' — create a book.</li>
%%% </ul>
%%% @end
%%%-------------------------------------------------------------------
-module(book_api_books_h).

-behaviour(cowboy_handler).

-export([init/2]).

-define(ALLOWED, [<<"GET">>, <<"HEAD">>, <<"POST">>]).

init(Req0, State) ->
    Req = book_api_http:handle(fun() -> dispatch(cowboy_req:method(Req0), Req0) end,
                               Req0),
    {ok, Req, State}.

dispatch(Method, Req) when Method =:= <<"GET">>; Method =:= <<"HEAD">> ->
    list(Req);
dispatch(<<"POST">>, Req) ->
    create(Req);
dispatch(_Other, Req) ->
    book_api_http:method_not_allowed(?ALLOWED, Req).

%%%===================================================================
%%% GET /books
%%%===================================================================

list(Req) ->
    Books =
        case author_filter(Req) of
            undefined -> book_store:list();
            Author -> book_store:list_by_author(Author)
        end,
    book_api_http:json(200, [book:to_map(B) || B <- Books], Req).

%% A blank `?author=' is treated as "no filter" rather than "authors named
%% empty string", which is what a client sending an unset form field means.
author_filter(Req) ->
    case proplists:get_value(<<"author">>, cowboy_req:parse_qs(Req)) of
        undefined -> undefined;
        true -> undefined;              %% bare `?author' with no value
        Value ->
            case string:trim(Value) of
                <<>> -> undefined;
                Trimmed -> Trimmed
            end
    end.

%%%===================================================================
%%% POST /books
%%%===================================================================

create(Req0) ->
    case book_api_http:read_json_body(Req0) of
        {error, Req} ->
            Req;
        {ok, Body, Req} ->
            case book:validate(Body) of
                {error, Errors} ->
                    book_api_http:error(400, <<"validation_failed">>,
                                        <<"The book could not be created">>,
                                        Errors, Req);
                {ok, Attrs} ->
                    {ok, Book} = book_store:create(Attrs),
                    Map = book:to_map(Book),
                    Location = ["/books/", integer_to_binary(map_get(<<"id">>, Map))],
                    Req1 = cowboy_req:set_resp_header(<<"location">>, Location, Req),
                    book_api_http:json(201, Map, Req1)
            end
    end.
