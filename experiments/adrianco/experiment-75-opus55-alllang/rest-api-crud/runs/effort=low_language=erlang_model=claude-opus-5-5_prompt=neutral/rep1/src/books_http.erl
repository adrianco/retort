%% inets httpd callback module implementing the REST API.
-module(books_http).
-include_lib("inets/include/httpd.hrl").
-export([do/1, validate/1]).

do(#mod{method = Method, request_uri = Uri, entity_body = Body}) ->
    {Path, Query} = case string:split(Uri, "?") of
                        [P, Q] -> {P, Q};
                        [P] -> {P, ""}
                    end,
    Segs = [S || S <- string:split(Path, "/", all), S =/= ""],
    {Code, Resp} = try route(Method, Segs, Query, Body)
                   catch _:_ -> {500, #{error => <<"internal error">>}}
                   end,
    reply(Code, Resp).

reply(Code, Resp) ->
    Bin = case Resp of none -> <<>>; _ -> iolist_to_binary(json:encode(Resp)) end,
    Headers = [{code, Code}, {content_type, "application/json"},
               {content_length, integer_to_list(byte_size(Bin))}],
    {proceed, [{response, {response, Headers, [binary_to_list(Bin)]}}]}.

route("GET", ["health"], _, _) -> {200, #{status => <<"ok">>}};
route("GET", ["books"], Q, _) ->
    Params = uri_string:dissect_query(Q),
    Author = case lists:keyfind("author", 1, Params) of
                 {_, A} -> unicode:characters_to_binary(A);
                 false -> undefined
             end,
    {200, books_store:list(Author)};
route("POST", ["books"], _, Body) ->
    with_valid(Body, fun(B) -> {201, books_store:create(B)} end);
route(M, ["books", IdS], _, Body) ->
    case string:to_integer(IdS) of
        {Id, ""} -> book_route(M, Id, Body);
        _ -> {404, #{error => <<"not found">>}}
    end;
route(_, _, _, _) -> {404, #{error => <<"not found">>}}.

book_route("GET", Id, _) -> found(books_store:get(Id), 200);
book_route("PUT", Id, Body) ->
    with_valid(Body, fun(B) -> found(books_store:update(Id, B), 200) end);
book_route("DELETE", Id, _) ->
    case books_store:delete(Id) of
        ok -> {204, none};
        not_found -> {404, #{error => <<"not found">>}}
    end;
book_route(_, _, _) -> {405, #{error => <<"method not allowed">>}}.

found({ok, B}, Code) -> {Code, B};
found(not_found, _) -> {404, #{error => <<"not found">>}}.

with_valid(Body, Fun) ->
    case catch json:decode(iolist_to_binary(Body)) of
        M when is_map(M) ->
            case validate(M) of
                {ok, B} -> Fun(B);
                {error, Errs} -> {400, #{error => <<"validation failed">>, details => Errs}}
            end;
        _ -> {400, #{error => <<"invalid JSON">>}}
    end.

%% Returns {ok, SanitizedBook} or {error, [Message]}.
validate(M) ->
    Errs = [E || E <- [req_str(M, <<"title">>), req_str(M, <<"author">>),
                       opt(M, <<"year">>, fun is_integer/1, <<"year must be an integer">>),
                       opt(M, <<"isbn">>, fun is_binary/1, <<"isbn must be a string">>)],
                 E =/= ok],
    case Errs of
        [] -> {ok, maps:with([<<"title">>, <<"author">>, <<"year">>, <<"isbn">>], M)};
        _ -> {error, Errs}
    end.

req_str(M, K) ->
    case maps:get(K, M, undefined) of
        V when is_binary(V) ->
            case string:trim(V) of <<>> -> <<K/binary, " is required">>; _ -> ok end;
        _ -> <<K/binary, " is required">>
    end.

opt(M, K, Pred, Msg) ->
    case maps:find(K, M) of
        error -> ok;
        {ok, null} -> ok;
        {ok, V} -> case Pred(V) of true -> ok; false -> Msg end
    end.
