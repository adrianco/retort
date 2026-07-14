-module(books_handler).

-export([init/2]).

init(Req0, State) ->
    Method = cowboy_req:method(Req0),
    Id = cowboy_req:binding(id, Req0),
    Req = route(Method, Id, Req0),
    {ok, Req, State}.

route(<<"POST">>, undefined, Req) ->
    create(Req);
route(<<"GET">>, undefined, Req) ->
    list(Req);
route(<<"GET">>, Id, Req) ->
    get_one(Id, Req);
route(<<"PUT">>, Id, Req) when Id =/= undefined ->
    update(Id, Req);
route(<<"DELETE">>, Id, Req) when Id =/= undefined ->
    delete(Id, Req);
route(_, _, Req) ->
    error_response(405, <<"method not allowed">>, Req).

create(Req0) ->
    {ok, Body, Req1} = cowboy_req:read_body(Req0),
    case parse_body(Body) of
        {ok, Map} ->
            case validate_create(Map) of
                {ok, Book} ->
                    {ok, Created} = books_db:create(Book),
                    json_response(201, book_to_json(Created), Req1);
                {error, Reason} ->
                    error_response(400, Reason, Req1)
            end;
        {error, Reason} ->
            error_response(400, Reason, Req1)
    end.

list(Req0) ->
    Qs = cowboy_req:parse_qs(Req0),
    Result = case lists:keyfind(<<"author">>, 1, Qs) of
        {<<"author">>, Author} -> books_db:list(Author);
        false -> books_db:list()
    end,
    {ok, Books} = Result,
    Json = [book_to_json(B) || B <- Books],
    json_response(200, Json, Req0).

get_one(Id, Req0) ->
    case books_db:get(Id) of
        {ok, Book} ->
            json_response(200, book_to_json(Book), Req0);
        {error, not_found} ->
            error_response(404, <<"not found">>, Req0)
    end.

update(Id, Req0) ->
    {ok, Body, Req1} = cowboy_req:read_body(Req0),
    case parse_body(Body) of
        {ok, Map} ->
            case validate_update(Map) of
                {ok, Updates} ->
                    case books_db:update(Id, Updates) of
                        {ok, Book} ->
                            json_response(200, book_to_json(Book), Req1);
                        {error, not_found} ->
                            error_response(404, <<"not found">>, Req1)
                    end;
                {error, Reason} ->
                    error_response(400, Reason, Req1)
            end;
        {error, Reason} ->
            error_response(400, Reason, Req1)
    end.

delete(Id, Req0) ->
    case books_db:delete(Id) of
        ok ->
            cowboy_req:reply(204, #{}, <<>>, Req0);
        {error, not_found} ->
            error_response(404, <<"not found">>, Req0)
    end.

parse_body(<<>>) ->
    {error, <<"empty body">>};
parse_body(Body) ->
    try json:decode(Body) of
        Map when is_map(Map) -> {ok, Map};
        _ -> {error, <<"expected JSON object">>}
    catch
        _:_ -> {error, <<"invalid JSON">>}
    end.

validate_create(Map) ->
    Title = maps:get(<<"title">>, Map, undefined),
    Author = maps:get(<<"author">>, Map, undefined),
    case validate_required(Title, Author) of
        ok ->
            Book = #{
                title => Title,
                author => Author,
                year => maps:get(<<"year">>, Map, null),
                isbn => maps:get(<<"isbn">>, Map, null)
            },
            {ok, Book};
        Err ->
            Err
    end.

validate_required(undefined, _) -> {error, <<"title is required">>};
validate_required(_, undefined) -> {error, <<"author is required">>};
validate_required(<<>>, _) -> {error, <<"title is required">>};
validate_required(_, <<>>) -> {error, <<"author is required">>};
validate_required(Title, _) when not is_binary(Title) ->
    {error, <<"title must be a string">>};
validate_required(_, Author) when not is_binary(Author) ->
    {error, <<"author must be a string">>};
validate_required(_, _) -> ok.

validate_update(Map) ->
    Allowed = [<<"title">>, <<"author">>, <<"year">>, <<"isbn">>],
    Updates = lists:foldl(
        fun(Key, Acc) ->
            case maps:find(Key, Map) of
                {ok, Value} -> Acc#{binary_to_atom(Key, utf8) => Value};
                error -> Acc
            end
        end, #{}, Allowed),
    case maps:size(Updates) of
        0 ->
            {error, <<"no fields to update">>};
        _ ->
            case check_non_empty(Updates) of
                ok -> {ok, Updates};
                Err -> Err
            end
    end.

check_non_empty(#{title := <<>>}) -> {error, <<"title cannot be empty">>};
check_non_empty(#{author := <<>>}) -> {error, <<"author cannot be empty">>};
check_non_empty(#{title := T}) when not is_binary(T) ->
    {error, <<"title must be a string">>};
check_non_empty(#{author := A}) when not is_binary(A) ->
    {error, <<"author must be a string">>};
check_non_empty(_) -> ok.

book_to_json(Book) ->
    #{
        id => maps:get(id, Book),
        title => maps:get(title, Book, null),
        author => maps:get(author, Book, null),
        year => maps:get(year, Book, null),
        isbn => maps:get(isbn, Book, null)
    }.

json_response(Code, Term, Req) ->
    Body = iolist_to_binary(json:encode(Term)),
    cowboy_req:reply(Code,
        #{<<"content-type">> => <<"application/json">>},
        Body, Req).

error_response(Code, Reason, Req) ->
    json_response(Code, #{error => Reason}, Req).
