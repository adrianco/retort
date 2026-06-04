-module(books_handler).

-export([init/2]).

init(Req0, State) ->
    Method = cowboy_req:method(Req0),
    Req = handle(Method, Req0),
    {ok, Req, State}.

handle(<<"GET">>, Req0) ->
    QS = cowboy_req:parse_qs(Req0),
    Books = case lists:keyfind(<<"author">>, 1, QS) of
        {_, Author} when is_binary(Author) ->
            book_store:list(Author);
        _ ->
            book_store:list()
    end,
    JsonBooks = [book_util:book_to_json(B) || B <- Books],
    book_util:json_reply(200, JsonBooks, Req0);

handle(<<"POST">>, Req0) ->
    {ok, BodyBin, Req1} = cowboy_req:read_body(Req0),
    case book_util:parse_body(BodyBin) of
        {ok, Data} ->
            case book_util:validate(Data) of
                ok ->
                    Book = book_store:create(Data),
                    book_util:json_reply(201, book_util:book_to_json(Book), Req1);
                {error, Msg} ->
                    book_util:error_reply(400, Msg, Req1)
            end;
        {error, Msg} ->
            book_util:error_reply(400, Msg, Req1)
    end;

handle(_, Req) ->
    cowboy_req:reply(
      405,
      #{<<"allow">> => <<"GET, POST">>},
      <<>>,
      Req).
