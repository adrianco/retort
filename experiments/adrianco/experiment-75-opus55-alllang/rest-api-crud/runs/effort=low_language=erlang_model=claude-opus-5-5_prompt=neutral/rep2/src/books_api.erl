%% Request routing, validation and JSON handling.
-module(books_api).
-export([handle/4, validate/1]).

handle(<<"GET">>, <<"/health">>, _, _) -> {200, #{<<"status">> => <<"ok">>}};
handle(M, <<"/books">>, Q, Body) -> collection(M, Q, Body);
handle(M, <<"/books/", IdBin/binary>>, _, Body) ->
    try binary_to_integer(IdBin) of
        Id -> item(M, Id, Body)
    catch _:_ -> not_found()
    end;
handle(_, _, _, _) -> not_found().

collection(<<"GET">>, Q, _) -> {200, books_store:list(maps:get(<<"author">>, Q, undefined))};
collection(<<"POST">>, _, Body) ->
    with_valid(Body, fun(Book) -> {201, books_store:create(Book)} end);
collection(_, _, _) -> not_allowed().

item(<<"GET">>, Id, _) -> result(books_store:get(Id));
item(<<"PUT">>, Id, Body) -> with_valid(Body, fun(Book) -> result(books_store:update(Id, Book)) end);
item(<<"DELETE">>, Id, _) ->
    case books_store:delete(Id) of ok -> {204, no_content}; E -> result(E) end;
item(_, _, _) -> not_allowed().

result({ok, B}) -> {200, B};
result({error, not_found}) -> not_found().

with_valid(Body, Fun) ->
    Decoded = try json:decode(Body) catch _:_ -> invalid_json end,
    case validate(Decoded) of
        {ok, Book} -> Fun(Book);
        {error, Errors} -> {400, #{<<"error">> => <<"validation failed">>, <<"details">> => Errors}}
    end.

%% Returns {ok, NormalisedBook} or {error, [Message]}.
validate(M) when is_map(M) ->
    Errors = lists:append([req_string(<<"title">>, M), req_string(<<"author">>, M),
                           opt(<<"year">>, M, fun is_integer/1, <<"year must be an integer">>),
                           opt(<<"isbn">>, M, fun is_binary/1, <<"isbn must be a string">>)]),
    case Errors of
        [] -> {ok, maps:with([<<"title">>, <<"author">>, <<"year">>, <<"isbn">>],
                             maps:merge(#{<<"year">> => null, <<"isbn">> => null}, M))};
        _ -> {error, Errors}
    end;
validate(_) -> {error, [<<"body must be a JSON object">>]}.

req_string(K, M) ->
    case maps:get(K, M, undefined) of
        V when is_binary(V) ->
            case string:trim(V) of <<>> -> [<<K/binary, " is required">>]; _ -> [] end;
        _ -> [<<K/binary, " is required">>]
    end.

opt(K, M, Pred, Msg) ->
    case maps:get(K, M, null) of null -> []; V -> case Pred(V) of true -> []; false -> [Msg] end end.

not_found() -> {404, #{<<"error">> => <<"not found">>}}.
not_allowed() -> {405, #{<<"error">> => <<"method not allowed">>}}.
