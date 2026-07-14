-module(books_handler).

-export([init/2, validate/1]).

init(Req0, State) ->
    Method = cowboy_req:method(Req0),
    Id = cowboy_req:binding(id, Req0),
    Req = handle(Method, Id, Req0),
    {ok, Req, State}.

handle(<<"GET">>, undefined, Req) ->
    QS = cowboy_req:parse_qs(Req),
    {ok, Books} = case proplists:get_value(<<"author">>, QS) of
        undefined -> books_db:list();
        Author -> books_db:list_by_author(Author)
    end,
    reply_json(200, Books, Req);

handle(<<"GET">>, Id, Req) ->
    case books_db:get(Id) of
        {ok, Book} -> reply_json(200, Book, Req);
        {error, not_found} -> reply_json(404, #{<<"error">> => <<"book not found">>}, Req)
    end;

handle(<<"POST">>, undefined, Req0) ->
    {ok, Body, Req1} = cowboy_req:read_body(Req0),
    case decode(Body) of
        {ok, Attrs} ->
            case validate(Attrs) of
                ok ->
                    {ok, Book} = books_db:create(Attrs),
                    reply_json(201, Book, Req1);
                {error, Msg} ->
                    reply_json(400, #{<<"error">> => Msg}, Req1)
            end;
        {error, _} ->
            reply_json(400, #{<<"error">> => <<"invalid JSON">>}, Req1)
    end;

handle(<<"PUT">>, Id, Req0) when Id =/= undefined ->
    {ok, Body, Req1} = cowboy_req:read_body(Req0),
    case decode(Body) of
        {ok, Attrs} ->
            case books_db:get(Id) of
                {error, not_found} ->
                    reply_json(404, #{<<"error">> => <<"book not found">>}, Req1);
                {ok, Existing} ->
                    Merged = maps:merge(Existing, Attrs),
                    case validate(Merged) of
                        ok ->
                            {ok, Updated} = books_db:update(Id, Attrs),
                            reply_json(200, Updated, Req1);
                        {error, Msg} ->
                            reply_json(400, #{<<"error">> => Msg}, Req1)
                    end
            end;
        {error, _} ->
            reply_json(400, #{<<"error">> => <<"invalid JSON">>}, Req1)
    end;

handle(<<"DELETE">>, Id, Req) when Id =/= undefined ->
    case books_db:delete(Id) of
        ok ->
            cowboy_req:reply(204, #{}, <<>>, Req);
        {error, not_found} ->
            reply_json(404, #{<<"error">> => <<"book not found">>}, Req)
    end;

handle(_, _, Req) ->
    reply_json(405, #{<<"error">> => <<"method not allowed">>}, Req).

reply_json(Status, Body, Req) ->
    cowboy_req:reply(Status,
        #{<<"content-type">> => <<"application/json">>},
        jsone:encode(Body),
        Req).

decode(<<>>) ->
    {error, empty};
decode(Body) ->
    try
        case jsone:decode(Body, [{object_format, map}]) of
            Map when is_map(Map) -> {ok, Map};
            _ -> {error, not_an_object}
        end
    catch
        _:_ -> {error, invalid_json}
    end.

validate(Map) ->
    Title = maps:get(<<"title">>, Map, undefined),
    Author = maps:get(<<"author">>, Map, undefined),
    case is_nonempty_binary(Title) of
        false ->
            {error, <<"title is required">>};
        true ->
            case is_nonempty_binary(Author) of
                false -> {error, <<"author is required">>};
                true -> ok
            end
    end.

is_nonempty_binary(<<>>) -> false;
is_nonempty_binary(B) when is_binary(B) -> true;
is_nonempty_binary(_) -> false.
