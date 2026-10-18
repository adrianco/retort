%% Shared helpers for the cowboy handlers: JSON replies, body parsing and
%% conversion between database rows and JSON objects.
-module(books_http).

-export([reply_json/3, reply_error/3, read_json_body/1, book_to_json/1, parse_id/1]).

reply_json(Status, Body, Req) ->
    cowboy_req:reply(Status, #{<<"content-type">> => <<"application/json">>},
                     json:encode(Body), Req).

reply_error(Status, Message, Req) ->
    reply_json(Status, #{<<"error">> => Message}, Req).

%% Reads the whole request body and decodes it as JSON.
-spec read_json_body(cowboy_req:req()) ->
          {ok, term(), cowboy_req:req()} | {error, invalid_json, cowboy_req:req()}.
read_json_body(Req0) ->
    {Body, Req} = read_all(Req0, <<>>),
    try json:decode(Body) of
        Decoded -> {ok, Decoded, Req}
    catch
        error:_ -> {error, invalid_json, Req}
    end.

read_all(Req0, Acc) ->
    case cowboy_req:read_body(Req0) of
        {ok, Data, Req} -> {<<Acc/binary, Data/binary>>, Req};
        {more, Data, Req} -> read_all(Req, <<Acc/binary, Data/binary>>)
    end.

book_to_json(#{id := Id, title := Title, author := Author, year := Year, isbn := Isbn}) ->
    #{<<"id">> => Id, <<"title">> => Title, <<"author">> => Author,
      <<"year">> => Year, <<"isbn">> => Isbn}.

%% Path ids must be positive integers; anything else can never match a book.
-spec parse_id(binary()) -> {ok, pos_integer()} | error.
parse_id(Bin) ->
    try binary_to_integer(Bin) of
        Id when Id > 0 -> {ok, Id};
        _ -> error
    catch
        error:badarg -> error
    end.
