-module(books_api_handler).
-behaviour(cowboy_handler).
-export([init/2, validate/1]).

init(Req0, State) ->
    Method = cowboy_req:method(Req0),
    PathInfo = cowboy_req:path_info(Req0),
    {Status, Payload, Req1} = route(Method, PathInfo, Req0),
    Body = case Status of 204 -> <<>>; _ -> jsx:encode(Payload) end,
    Req = cowboy_req:reply(Status, #{<<"content-type">> => <<"application/json">>}, Body, Req1),
    {ok, Req, State}.

route(<<"GET">>, [<<"health">>], Req) -> {200, #{status => ok}, Req};
route(<<"GET">>, [<<"books">>], Req) ->
    Author = case proplists:get_value(<<"author">>, cowboy_req:parse_qs(Req)) of undefined -> undefined; A -> A end,
    {200, books_api_store:list(Author), Req};
route(<<"POST">>, [<<"books">>], Req0) ->
    {Body, Req} = read_json(Req0),
    case validate(Body) of
        ok -> {201, books_api_store:create(Body), Req};
        {error, Why} -> {400, #{error => Why}, Req}
    end;
route(<<"GET">>, [<<"books">>, Id0], Req) -> respond_book(books_api_store:get(id(Id0)), Req);
route(<<"PUT">>, [<<"books">>, Id0], Req0) ->
    {Body, Req} = read_json(Req0),
    case validate(Body) of
        ok -> respond_book(books_api_store:update(id(Id0), Body), Req);
        {error, Why} -> {400, #{error => Why}, Req}
    end;
route(<<"DELETE">>, [<<"books">>, Id0], Req) ->
    case books_api_store:delete(id(Id0)) of
        [#{<<"changes">> := 1}] -> {204, #{}, Req};
        _ -> {404, #{error => not_found}, Req}
    end;
route(_, _, Req) -> {404, #{error => not_found}, Req}.

read_json(Req0) ->
    case cowboy_req:read_body(Req0) of
        {ok, Data, Req} -> try {jsx:decode(Data, [return_maps]), Req} catch _:_ -> {#{}, Req} end;
        {more, Data, Req} -> try {jsx:decode(Data, [return_maps]), Req} catch _:_ -> {#{}, Req} end
    end.
validate(Body) when is_map(Body) ->
    case {maps:get(<<"title">>, Body, undefined), maps:get(<<"author">>, Body, undefined)} of
        {T, A} when is_binary(T), byte_size(T) > 0, is_binary(A), byte_size(A) > 0 -> ok;
        _ -> {error, <<"title and author are required">>}
    end;
validate(_) -> {error, <<"expected a JSON object">>}.
respond_book(not_found, Req) -> {404, #{error => not_found}, Req};
respond_book({error, _}, Req) -> {500, #{error => storage_error}, Req};
respond_book(Book, Req) when is_map(Book) -> {200, Book, Req};
respond_book(_, Req) -> {404, #{error => not_found}, Req}.
id(Bin) -> try binary_to_integer(Bin) catch _:_ -> -1 end.
