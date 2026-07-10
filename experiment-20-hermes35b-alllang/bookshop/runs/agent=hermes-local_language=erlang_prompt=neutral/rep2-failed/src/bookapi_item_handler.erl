-module(bookapi_item_handler).

-export([init/3]).

init(Req, Opts, State) ->
    Method = cowboy_req:method(Req),
    case cowboy_req:path_param(<<"id">>, Req) of
        IdStr when is_list(IdStr) ->
            case catch list_to_integer(IdStr) of
                Id when is_integer(Id) ->
                    handle_item(Req, Id, Method, Opts, State);
                _ ->
                    cowboy_req:reply(400,
                        #{<<"content-type">> => <<"application/json">>},
                        jiffy:encode(#{error => <<"invalid_id">>}), Req),
                    {ok, Req, State, Opts}
            end;
        _ ->
            cowboy_req:reply(400,
                #{<<"content-type">> => <<"application/json">>},
                jiffy:encode(#{error => <<"missing_id">>}), Req),
            {ok, Req, State, Opts}
    end.

handle_item(Req, Id, <<"GET">>, Opts, State) ->
    case bookapi_db:get_book(Id) of
        {ok, Book} ->
            cowboy_req:reply(200,
                #{<<"content-type">> => <<"application/json">>},
                jiffy:encode(Book), Req);
        {error, not_found} ->
            cowboy_req:reply(404,
                #{<<"content-type">> => <<"application/json">>},
                jiffy:encode(#{error => <<"book_not_found">>}), Req)
    end,
    {ok, Req, State, Opts};

handle_item(Req, Id, <<"PUT">>, Opts, State) ->
    Body = cowboy_req:body(Req),
    Map = jiffy:decode(Body, [return_maps]),
    case bookapi_db:update_book(Id, Map) of
        {ok, Book} ->
            cowboy_req:reply(200,
                #{<<"content-type">> => <<"application/json">>},
                jiffy:encode(Book), Req);
        {error, not_found} ->
            cowboy_req:reply(404,
                #{<<"content-type">> => <<"application/json">>},
                jiffy:encode(#{error => <<"book_not_found">>}), Req);
        {error, Reason} ->
            cowboy_req:reply(500,
                #{<<"content-type">> => <<"application/json">>},
                jiffy:encode(#{error => Reason}), Req)
    end,
    {ok, Req, State, Opts};

handle_item(Req, Id, <<"DELETE">>, Opts, State) ->
    case bookapi_db:delete_book(Id) of
        {ok, deleted} ->
            cowboy_req:reply(200,
                #{<<"content-type">> => <<"application/json">>},
                jiffy:encode(#{message => <<"book_deleted">>}), Req);
        {error, not_found} ->
            cowboy_req:reply(404,
                #{<<"content-type">> => <<"application/json">>},
                jiffy:encode(#{error => <<"book_not_found">>}), Req)
    end,
    {ok, Req, State, Opts};

handle_item(Req, _Id, _Method, Opts, State) ->
    cowboy_req:reply(405,
        #{<<"content-type">> => <<"application/json">>},
        jiffy:encode(#{error => <<"method_not_allowed">>}), Req),
    {ok, Req, State, Opts}.
