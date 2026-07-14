-module(bookapi_collection_handler).

-export([init/3]).

init(Req, Opts, State) ->
    Method = cowboy_req:method(Req),
    case Method of
        <<"POST">> ->
            handle_create(Req, Opts, State);
        <<"GET">> ->
            handle_list(Req, Opts, State);
        _ ->
            cowboy_req:reply(405,
                #{<<"content-type">> => <<"application/json">>},
                jiffy:encode(#{error => <<"method_not_allowed">>}), Req),
            {ok, Req, State, Opts}
    end.

handle_create(Req, Opts, State) ->
    Body = cowboy_req:body(Req),
    case jiffy:decode(Body, [return_maps]) of
        Map when is_map(Map) ->
            case bookapi_db:create_book(Map) of
                {ok, Book} ->
                    cowboy_req:reply(201,
                        #{<<"content-type">> => <<"application/json">>},
                        jiffy:encode(Book), Req);
                {error, missing_field} ->
                    cowboy_req:reply(400,
                        #{<<"content-type">> => <<"application/json">>},
                        jiffy:encode(#{error => <<"title and author are required">>}), Req);
                {error, Reason} ->
                    cowboy_req:reply(500,
                        #{<<"content-type">> => <<"application/json">>},
                        jiffy:encode(#{error => Reason}), Req)
            end;
        _ ->
            cowboy_req:reply(400,
                #{<<"content-type">> => <<"application/json">>},
                jiffy:encode(#{error => <<"invalid_json">>}), Req)
    end,
    {ok, Req, State, Opts}.

handle_list(Req, Opts, State) ->
    AuthorParam = cowboy_req:qs_param(<<"author">>, Req, undefined),
    case AuthorParam of
        undefined ->
            Books = bookapi_db:list_books(),
            cowboy_req:reply(200,
                #{<<"content-type">> => <<"application/json">>},
                jiffy:encode(Books), Req);
        AuthorParam ->
            Books = bookapi_db:list_books(AuthorParam),
            cowboy_req:reply(200,
                #{<<"content-type">> => <<"application/json">>},
                jiffy:encode(Books), Req)
    end,
    {ok, Req, State, Opts}.
