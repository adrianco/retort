-module(book_api_handler).

-export([init/2, handle/2, terminate/3]).

init(Req, _Opts) ->
    {ok, Req, #{}}.

handle(Req, State) ->
    Method = cowboy_req:method(Req),
    Path = binary_to_list(cowboy_req:path(Req)),
    do_handle(Method, Path, Req, State),
    {ok, Req, State}.

terminate(_Reason, _Req, _State) ->
    ok.

%% Route dispatch
do_handle('GET', "/health", Req, _State) ->
    Body = jiffy:encode(#{status => "ok"}),
    cowboy_req:reply(200, #{<<"content-type">> => <<"application/json">>}, Body, Req);
do_handle('GET', "/books", Req, _State) ->
    Author = binary_to_list(cowboy_req:qs_param(<<"author">>, Req, undefined)),
    do_list_books(Author, Req);
do_handle('POST', "/books", Req, _State) ->
    do_create_book(Req);
do_handle('GET', Path, Req, _State) ->
    do_path_dispatch(get, Path, Req, _State);
do_handle('PUT', Path, Req, _State) ->
    do_path_dispatch(update, Path, Req, _State);
do_handle('DELETE', Path, Req, _State) ->
    do_path_dispatch(delete, Path, Req, _State);
do_handle(_, _, Req, _State) ->
    Body = jiffy:encode(#{error => "not_found"}),
    cowboy_req:reply(404, #{<<"content-type">> => <<"application/json">>}, Body, Req).

do_path_dispatch(get, Path, Req, _State) ->
    do_extract_id(Path, Req, fun do_get_book/2);
do_path_dispatch(update, Path, Req, _State) ->
    do_extract_id(Path, Req, fun do_update_book/2);
do_path_dispatch(delete, Path, Req, _State) ->
    do_extract_id(Path, Req, fun do_delete_book/2).

do_extract_id(Path, Req, Fun) ->
    case re:run(Path, "^/books/([0-9]+)$", [{capture, none}]) of
        {match, [IdStr]} ->
            Id = list_to_integer(IdStr),
            Fun(Id, Req);
        nomatch ->
            Body = jiffy:encode(#{error => "not_found"}),
            cowboy_req:reply(404, #{<<"content-type">> => <<"application/json">>}, Body, Req)
    end.

%% List books
do_list_books(undefined, Req) ->
    case book_db:get_all_books() of
        {ok, Books} ->
            Json = jiffy:encode(#{books => Books}),
            cowboy_req:reply(200, #{<<"content-type">> => <<"application/json">>}, Json, Req);
        {error, Reason} ->
            Body = jiffy:encode(#{error => Reason}),
            cowboy_req:reply(500, #{<<"content-type">> => <<"application/json">>}, Body, Req)
    end;
do_list_books(Author, Req) ->
    case book_db:get_all_books(Author) of
        {ok, Books} ->
            Json = jiffy:encode(#{books => Books}),
            cowboy_req:reply(200, #{<<"content-type">> => <<"application/json">>}, Json, Req);
        {error, Reason} ->
            Body = jiffy:encode(#{error => Reason}),
            cowboy_req:reply(500, #{<<"content-type">> => <<"application/json">>}, Body, Req)
    end.

%% Create book
do_create_book(Req) ->
    Raw = cowboy_req:body(Req),
    case jiffy:decode(Raw, [return_maps]) of
        #{<<"title">> := Title, <<"author">> := Author} = JsonData ->
            Year = maps:get(<<"year">>, JsonData, undefined),
            ISBN = maps:get(<<"isbn">>, JsonData, undefined),
            BookProps = build_book_props(Title, Author, Year, ISBN),
            case book_db:create_book(BookProps) of
                {ok, Book} ->
                    Json = jiffy:encode(Book),
                    cowboy_req:reply(201, #{<<"content-type">> => <<"application/json">>}, Json, Req);
                {error, Reason} ->
                    ErrorBody = jiffy:encode(#{error => Reason}),
                    cowboy_req:reply(400, #{<<"content-type">> => <<"application/json">>}, ErrorBody, Req)
            end;
        _ ->
            ErrorBody = jiffy:encode(#{error => "title and author are required"}),
            cowboy_req:reply(400, #{<<"content-type">> => <<"application/json">>}, ErrorBody, Req)
    end.

%% Get book
do_get_book(Id, Req) ->
    case book_db:get_book(Id) of
        {ok, Book} ->
            Json = jiffy:encode(Book),
            cowboy_req:reply(200, #{<<"content-type">> => <<"application/json">>}, Json, Req);
        {error, not_found} ->
            Body = jiffy:encode(#{error => "book not found"}),
            cowboy_req:reply(404, #{<<"content-type">> => <<"application/json">>}, Body, Req)
    end.

%% Update book
do_update_book(Id, Req) ->
    Raw = cowboy_req:body(Req),
    case jiffy:decode(Raw, [return_maps]) of
        JsonData when is_map(JsonData) ->
            Title = maps:get(<<"title">>, JsonData, undefined),
            Author = maps:get(<<"author">>, JsonData, undefined),
            Year = maps:get(<<"year">>, JsonData, undefined),
            ISBN = maps:get(<<"isbn">>, JsonData, undefined),
            BookProps = build_book_props(Title, Author, Year, ISBN),
            case book_db:update_book(Id, BookProps) of
                {ok, Book} ->
                    Json = jiffy:encode(Book),
                    cowboy_req:reply(200, #{<<"content-type">> => <<"application/json">>}, Json, Req);
                {error, Reason} ->
                    ErrorBody = jiffy:encode(#{error => Reason}),
                    cowboy_req:reply(400, #{<<"content-type">> => <<"application/json">>}, ErrorBody, Req)
            end;
        _ ->
            ErrorBody = jiffy:encode(#{error => "invalid request body"}),
            cowboy_req:reply(400, #{<<"content-type">> => <<"application/json">>}, ErrorBody, Req)
    end.

%% Delete book
do_delete_book(Id, Req) ->
    case book_db:delete_book(Id) of
        {ok, deleted} ->
            Body = jiffy:encode(#{message => "book deleted"}),
            cowboy_req:reply(200, #{<<"content-type">> => <<"application/json">>}, Body, Req);
        {error, not_found} ->
            Body = jiffy:encode(#{error => "book not found"}),
            cowboy_req:reply(404, #{<<"content-type">> => <<"application/json">>}, Body, Req)
    end.

%% Helpers
build_book_props(Title, Author, Year, ISBN) ->
    PropList = [
        {title, convert(Title)},
        {author, convert(Author)},
        {isbn, convert(ISBN)}
    ],
    case Year of
        undefined -> maps:from_list(PropList);
        _ -> maps:from_list([{year, convert_int(Year)} | PropList])
    end.

convert(undefined) -> undefined;
convert(B) when is_binary(B) -> binary_to_list(B);
convert(V) when is_list(V) -> V.

convert_int(undefined) -> undefined;
convert_int(I) when is_integer(I) -> I;
convert_int(B) when is_binary(B) -> binary_to_integer(B).
