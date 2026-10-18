%% Routing, validation and JSON-level request handling. Independent of sockets.
-module(books_handler).

-export([handle/3]).

%% Returns {HttpStatus, Term}; Term is JSON-encodable, or undefined for no body.
handle(Method, Target, Body) ->
    {Path, Query} = split_target(Target),
    route(Method, string:lexemes(Path, "/"), Query, Body).

split_target(Target) ->
    case binary:split(Target, <<"?">>) of
        [Path] -> {Path, <<>>};
        [Path, Query] -> {Path, Query}
    end.

route(<<"GET">>, [<<"health">>], _Query, _Body) ->
    {200, #{<<"status">> => <<"ok">>}};
route(<<"POST">>, [<<"books">>], _Query, Body) ->
    create_book(Body);
route(<<"GET">>, [<<"books">>], Query, _Body) ->
    list_books(Query);
route(<<"GET">>, [<<"books">>, Id], _Query, _Body) ->
    with_id(Id, fun get_book/1);
route(<<"PUT">>, [<<"books">>, Id], _Query, Body) ->
    with_id(Id, fun(BookId) -> update_book(BookId, Body) end);
route(<<"DELETE">>, [<<"books">>, Id], _Query, _Body) ->
    with_id(Id, fun delete_book/1);
route(_, [<<"health">>], _Query, _Body) ->
    problem(405, "method not allowed");
route(_, [<<"books">>], _Query, _Body) ->
    problem(405, "method not allowed");
route(_, [<<"books">>, _Id], _Query, _Body) ->
    problem(405, "method not allowed");
route(_, _Segments, _Query, _Body) ->
    problem(404, "not found").

create_book(Body) ->
    case decode(Body) of
        {error, Msg} ->
            problem(400, Msg);
        {ok, Map} ->
            case validate(Map, create) of
                {error, Errors} ->
                    validation_error(Errors);
                {ok, Changes} ->
                    Defaults = #{<<"year">> => null, <<"isbn">> => null},
                    {ok, Book} = books_store:create(maps:merge(Defaults, Changes)),
                    {201, Book}
            end
    end.

list_books(Query) ->
    {ok, Books} = books_store:list(author_param(Query)),
    {200, Books}.

get_book(Id) ->
    case books_store:get(Id) of
        {ok, Book} -> {200, Book};
        not_found -> book_not_found()
    end.

update_book(Id, Body) ->
    case decode(Body) of
        {error, Msg} ->
            problem(400, Msg);
        {ok, Map} ->
            case validate(Map, update) of
                {error, Errors} ->
                    validation_error(Errors);
                {ok, Changes} ->
                    case books_store:update(Id, Changes) of
                        {ok, Book} -> {200, Book};
                        not_found -> book_not_found()
                    end
            end
    end.

delete_book(Id) ->
    case books_store:delete(Id) of
        ok -> {204, undefined};
        not_found -> book_not_found()
    end.

with_id(IdBin, Fun) ->
    case string:to_integer(IdBin) of
        {Id, <<>>} when Id > 0 -> Fun(Id);
        _ -> problem(400, "invalid book id")
    end.

author_param(Query) ->
    case uri_string:dissect_query(binary_to_list(Query)) of
        Params when is_list(Params) ->
            case lists:keyfind("author", 1, Params) of
                {"author", Author} when is_list(Author) ->
                    unicode:characters_to_binary(Author);
                _ ->
                    undefined
            end;
        _ ->
            undefined
    end.

decode(Body) ->
    try json:decode(Body) of
        Map when is_map(Map) -> {ok, Map};
        _ -> {error, <<"request body must be a JSON object">>}
    catch
        _:_ -> {error, <<"invalid JSON body">>}
    end.

%% Mode is create (title and author required) or update (fields optional).
%% JSON null is treated the same as an absent field.
validate(Map, Mode) ->
    Errors = text_errors(<<"title">>, Map, Mode) ++
        text_errors(<<"author">>, Map, Mode) ++
        year_errors(Map) ++
        isbn_errors(Map),
    case Errors of
        [] -> {ok, changes(Map)};
        _ -> {error, Errors}
    end.

text_errors(Key, Map, Mode) ->
    case maps:get(Key, Map, null) of
        null when Mode =:= create -> [<<Key/binary, " is required">>];
        null -> [];
        Value when is_binary(Value) ->
            case string:trim(Value) of
                <<>> -> [<<Key/binary, " must not be empty">>];
                _ -> []
            end;
        _ -> [<<Key/binary, " must be a string">>]
    end.

year_errors(Map) ->
    case maps:get(<<"year">>, Map, null) of
        null -> [];
        Year when is_integer(Year), Year >= 0 -> [];
        _ -> [<<"year must be a non-negative integer">>]
    end.

isbn_errors(Map) ->
    case maps:get(<<"isbn">>, Map, null) of
        null -> [];
        Isbn when is_binary(Isbn) -> [];
        _ -> [<<"isbn must be a string">>]
    end.

changes(Map) ->
    maps:from_list([{Key, trim(Value)} ||
        Key <- [<<"title">>, <<"author">>, <<"year">>, <<"isbn">>],
        Value <- [maps:get(Key, Map, null)],
        Value =/= null]).

trim(Value) when is_binary(Value) -> string:trim(Value);
trim(Value) -> Value.

validation_error(Errors) ->
    {400, #{<<"error">> => <<"validation failed">>, <<"details">> => Errors}}.

book_not_found() ->
    problem(404, "book not found").

problem(Status, Msg) ->
    {Status, #{<<"error">> => unicode:characters_to_binary(Msg)}}.
