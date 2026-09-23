%% Routing, validation and request handling. Returns {Status, JsonTerm | no_content}.
-module(books_api).
-export([handle/3, validate/1]).

handle(Method, RawPath, Body) ->
    {Path, Query} = case binary:split(RawPath, <<"?">>) of
                        [P, Q] -> {P, uri_string:dissect_query(Q)};
                        [P] -> {P, []}
                    end,
    route(Method, [S || S <- binary:split(Path, <<"/">>, [global]), S =/= <<>>], Query, Body).

route(<<"GET">>, [<<"health">>], _, _) ->
    {200, #{<<"status">> => <<"ok">>}};
route(<<"GET">>, [<<"books">>], Q, _) ->
    Author = case lists:keyfind(<<"author">>, 1, Q) of
                 {_, A} when is_binary(A) -> A;
                 _ -> undefined
             end,
    {200, books_db:list(Author)};
route(<<"POST">>, [<<"books">>], _, Body) ->
    with_book(Body, fun(B) -> {ok, R} = books_db:create(B), {201, R} end);
route(Method, [<<"books">>, IdBin], _, Body) ->
    case parse_id(IdBin) of
        error -> not_found();
        Id -> book_route(Method, Id, Body)
    end;
route(_, [<<"books">>], _, _) -> method_not_allowed();
route(_, [<<"health">>], _, _) -> method_not_allowed();
route(_, _, _, _) -> not_found().

book_route(<<"GET">>, Id, _) ->
    case books_db:get(Id) of {ok, B} -> {200, B}; _ -> not_found() end;
book_route(<<"PUT">>, Id, Body) ->
    with_book(Body, fun(B) ->
        case books_db:update(Id, B) of {ok, R} -> {200, R}; _ -> not_found() end
    end);
book_route(<<"DELETE">>, Id, _) ->
    case books_db:delete(Id) of ok -> {204, no_content}; _ -> not_found() end;
book_route(_, _, _) -> method_not_allowed().

with_book(Body, Fun) ->
    Decoded = try json:decode(Body) catch _:_ -> invalid_json end,
    case Decoded of
        invalid_json -> error_resp(400, <<"invalid JSON body">>);
        _ -> case validate(Decoded) of
                 {ok, Book} -> Fun(Book);
                 {error, Msgs} -> {400, #{<<"error">> => <<"validation failed">>,
                                          <<"details">> => Msgs}}
             end
    end.

%% Validates a decoded JSON object; returns a normalized book map.
validate(M) when is_map(M) ->
    Checks = [{<<"title">>, required_string}, {<<"author">>, required_string},
              {<<"year">>, optional_int}, {<<"isbn">>, optional_string}],
    {Book, Errs} = lists:foldl(fun({K, T}, {B, E}) ->
        case check(T, maps:get(K, M, null)) of
            {ok, V} -> {B#{K => V}, E};
            {error, Msg} -> {B, [<<K/binary, " ", Msg/binary>> | E]}
        end
    end, {#{}, []}, Checks),
    case Errs of [] -> {ok, Book}; _ -> {error, lists:reverse(Errs)} end;
validate(_) -> {error, [<<"body must be a JSON object">>]}.

check(required_string, V) when is_binary(V) ->
    case string:trim(V) of <<>> -> {error, <<"is required">>}; _ -> {ok, V} end;
check(required_string, _) -> {error, <<"is required">>};
check(optional_int, null) -> {ok, null};
check(optional_int, V) when is_integer(V) -> {ok, V};
check(optional_int, _) -> {error, <<"must be an integer">>};
check(optional_string, null) -> {ok, null};
check(optional_string, V) when is_binary(V) -> {ok, V};
check(optional_string, _) -> {error, <<"must be a string">>}.

parse_id(B) ->
    try binary_to_integer(B) of I when I > 0 -> I; _ -> error
    catch _:_ -> error end.

not_found() -> error_resp(404, <<"not found">>).
method_not_allowed() -> error_resp(405, <<"method not allowed">>).
error_resp(S, Msg) -> {S, #{<<"error">> => Msg}}.
