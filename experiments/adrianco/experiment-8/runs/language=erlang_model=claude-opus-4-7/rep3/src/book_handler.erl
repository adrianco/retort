-module(book_handler).

-export([init/2]).

init(Req0, State) ->
    IdBin = cowboy_req:binding(id, Req0),
    Req = case parse_id(IdBin) of
        {ok, Id} ->
            handle(cowboy_req:method(Req0), Id, Req0);
        error ->
            book_util:error_reply(400, <<"invalid id">>, Req0)
    end,
    {ok, Req, State}.

parse_id(Bin) when is_binary(Bin) ->
    try {ok, binary_to_integer(Bin)}
    catch _:_ -> error
    end;
parse_id(_) ->
    error.

handle(<<"GET">>, Id, Req) ->
    case book_store:find(Id) of
        {ok, Book} ->
            book_util:json_reply(200, book_util:book_to_json(Book), Req);
        {error, not_found} ->
            book_util:error_reply(404, <<"book not found">>, Req)
    end;

handle(<<"PUT">>, Id, Req0) ->
    {ok, BodyBin, Req1} = cowboy_req:read_body(Req0),
    case book_util:parse_body(BodyBin) of
        {ok, Data} ->
            case book_util:validate(Data) of
                ok ->
                    case book_store:update(Id, Data) of
                        {ok, Book} ->
                            book_util:json_reply(200, book_util:book_to_json(Book), Req1);
                        {error, not_found} ->
                            book_util:error_reply(404, <<"book not found">>, Req1)
                    end;
                {error, Msg} ->
                    book_util:error_reply(400, Msg, Req1)
            end;
        {error, Msg} ->
            book_util:error_reply(400, Msg, Req1)
    end;

handle(<<"DELETE">>, Id, Req) ->
    case book_store:delete(Id) of
        ok ->
            cowboy_req:reply(204, #{}, <<>>, Req);
        {error, not_found} ->
            book_util:error_reply(404, <<"book not found">>, Req)
    end;

handle(_, _Id, Req) ->
    cowboy_req:reply(
      405,
      #{<<"allow">> => <<"GET, PUT, DELETE">>},
      <<>>,
      Req).
