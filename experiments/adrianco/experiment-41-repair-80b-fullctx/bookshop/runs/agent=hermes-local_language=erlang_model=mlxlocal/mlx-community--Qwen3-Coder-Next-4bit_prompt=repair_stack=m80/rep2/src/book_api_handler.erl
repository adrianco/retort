-module(book_api_handler).
-export([handle_request/1]).

%% Handle incoming HTTP requests
handle_request(Req) ->
    %% Parse the request
    Method = case proplists:get_value(method, Req) of
        {MethodStr, _} -> MethodStr
    end,
    Path = case proplists:get_value(path, Req) of
        {PathStr, _} -> PathStr
    end,
    Body = case proplists:get_value(body, Req) of
        {BodyStr, _} -> BodyStr
    end,
    
    %% Route the request
    case {Method, Path} of
        {get, "/health"} ->
            send_response(200, #{<<"status">> => <<"ok">>});
        {get, "/books"} ->
            handle_books_list(Req);
        {post, "/books"} ->
            handle_books_create(Req, Body);
        {get, {"/books", Id}} ->
            handle_book_get(Id, Req);
        {put, {"/books", Id}} ->
            handle_book_update(Id, Req, Body);
        {delete, {"/books", Id}} ->
            handle_book_delete(Id, Req);
        _ ->
            send_response(404, #{<<"error">> => <<"Not found">>})
    end.

%% List all books with optional author filter
handle_books_list(Req) ->
    Author = case proplists:get_value(author, Req) of
        undefined -> undefined;
        {AuthorStr, _} -> AuthorStr
    end,
    case book_api_db:get_all_books() of
        {ok, Books} ->
            FilteredBooks = case Author of
                undefined -> Books;
                _ -> books_filter_by_author(Books, Author)
            end,
            send_response(200, #{<<"books">> => FilteredBooks});
        Error ->
            send_response(500, #{<<"error">> => atom_to_list(Error)})
    end.

%% Create a new book
handle_books_create(_Req, Body) ->
    case parse_json(Body) of
        {ok, Book} ->
            case book_api_db:create_book(Book) of
                {ok, CreatedBook} ->
                    send_response(201, CreatedBook);
                {error, Reason} ->
                    send_response(400, #{<<"error">> => atom_to_list(Reason)})
            end;
        {error, Reason} ->
            send_response(400, #{<<"error">> => Reason})
    end.

%% Get a single book
handle_book_get(IdStr, _Req) ->
    case string_to_integer(IdStr) of
        {ok, Id} ->
            case book_api_db:get_book_by_id(Id) of
                {ok, Book} ->
                    send_response(200, Book);
                {error, not_found} ->
                    send_response(404, #{<<"error">> => <<"Book not found">>});
                {error, Reason} ->
                    send_response(400, #{<<"error">> => atom_to_list(Reason)})
            end;
        error ->
            send_response(400, #{<<"error">> => <<"Invalid book ID">>})
    end.

%% Update a book
handle_book_update(IdStr, _Req, Body) ->
    case string_to_integer(IdStr) of
        {ok, Id} ->
            case parse_json(Body) of
                {ok, Book} ->
                    case book_api_db:update_book(Id, Book) of
                        {ok, UpdatedBook} ->
                            send_response(200, UpdatedBook);
                        {error, not_found} ->
                            send_response(404, #{<<"error">> => <<"Book not found">>});
                        {error, Reason} ->
                            send_response(400, #{<<"error">> => atom_to_list(Reason)})
                    end;
                {error, Reason} ->
                    send_response(400, #{<<"error">> => Reason})
            end;
        error ->
            send_response(400, #{<<"error">> => <<"Invalid book ID">>})
    end.

%% Delete a book
handle_book_delete(IdStr, _Req) ->
    case string_to_integer(IdStr) of
        {ok, Id} ->
            case book_api_db:delete_book(Id) of
                {ok, deleted} ->
                    send_response(204, undefined);
                {error, not_found} ->
                    send_response(404, #{<<"error">> => <<"Book not found">>});
                {error, Reason} ->
                    send_response(400, #{<<"error">> => atom_to_list(Reason)})
            end;
        error ->
            send_response(400, #{<<"error">> => <<"Invalid book ID">>})
    end.

%% Send HTTP response
send_response(Status, Body) when is_map(Body) ->
    JsonBody = json_encode(Body),
    {response, Status, [{<<"content-type">>, <<"application/json">>}], JsonBody};
send_response(Status, undefined) ->
    {response, Status, [], <<>>}.

%% Helper functions
string_to_integer(String) when is_binary(String) ->
    try
        {ok, list_to_integer(binary_to_list(String))}
    catch
        _:_ -> error
    end;
string_to_integer(String) when is_list(String) ->
    try
        {ok, list_to_integer(String)}
    catch
        _:_ -> error
    end;
string_to_integer(Integer) when is_integer(Integer) ->
    {ok, Integer};
string_to_integer(_) ->
    error.

books_filter_by_author(Books, Author) ->
    [Book || Book <- Books, maps:get(author, Book) =:= Author].

%% Simple JSON encoder
json_encode(Data) when is_map(Data) ->
    lists:flatten(json_encode_map(Data));
json_encode(Data) when is_list(Data) ->
    lists:flatten(json_encode_list(Data));
json_encode(Atom) when is_atom(Atom) ->
    atom_to_list(Atom);
json_encode(Binary) when is_binary(Binary) ->
    json_encode_string(Binary);
json_encode(Integer) when is_integer(Integer) ->
    integer_to_list(Integer);
json_encode(Float) when is_float(Float) ->
    float_to_list(Float);
json_encode(true) -> "true";
json_encode(false) -> "false";
json_encode(undefined) -> "null";
json_encode(null) -> "null".

json_encode_map(Map) ->
    Items = [json_encode_key_value(K, V) || {K, V} <- maps:to_list(Map)],
    ["{", string:join(Items, ","), "}"].

json_encode_key_value(Key, Value) ->
    [json_encode_string(Key), ":", json_encode(Value)].

json_encode_list(List) ->
    Items = [json_encode(Item) || Item <- List],
    ["[", string:join(Items, ","), "]"].

json_encode_string(Str) when is_binary(Str) ->
    json_encode_string(binary_to_list(Str));
json_encode_string(Str) when is_list(Str) ->
    "\"" ++ json_encode_string_chars(Str) ++ "\"".

json_encode_string_chars([]) -> [];
json_encode_string_chars([C | Rest]) when C >= 32 andalso C =< 126 andalso C /= $\ andalso C /= $\\ ->
    [C | json_encode_string_chars(Rest)];
json_encode_string_chars([$\\ | Rest]) ->
    "\\\\" ++ json_encode_string_chars(Rest);
json_encode_string_chars([$\" | Rest]) ->
    "\\\"" ++ json_encode_string_chars(Rest);
json_encode_string_chars([C | Rest]) when C < 32 ->
    io_lib:format("\\u~4.16.0B", [C]) ++ json_encode_string_chars(Rest);
json_encode_string_chars([C | Rest]) ->
    [C | json_encode_string_chars(Rest)].

%% Simple JSON parser
parse_json(Body) when is_binary(Body) ->
    json_parse(binary_to_list(Body));
parse_json(Body) when is_list(Body) ->
    json_parse(Body).

json_parse(Str) ->
    Str1 = skip_whitespace(Str),
    case Str1 of
        [$"] -> 
            {error, invalid_json};
        [$" | _] -> 
            {ok, JsonMap} = json_parse_object(Str1, #{}),
            {ok, JsonMap};
        _ -> {error, invalid_json}
    end.

json_parse_object([$" | Rest], Acc) ->
    {Key, Rest1} = json_parse_string_value(Rest),
    Rest2 = skip_whitespace(Rest1),
    case Rest2 of
        [$: | Rest3] ->
            Rest4 = skip_whitespace(Rest3),
            {Value, Rest5} = json_parse_value(Rest4),
            Acc2 = maps:put(Key, Value, Acc),
            json_parse_next(Rest5, Acc2);
        _ -> {error, expected_colon}
    end.

json_parse_next([$, | Rest], Acc) ->
    json_parse_object(skip_whitespace(Rest), Acc);
json_parse_next([$} | Rest], Acc) ->
    {Acc, skip_whitespace(Rest)};
json_parse_next(_, _) -> {error, invalid_json}.

json_parse_string_value([$" | Rest]) ->
    json_parse_string_value(Rest, []).

json_parse_string_value([$" | Rest], Acc) ->
    {list_to_binary(lists:reverse(Acc)), Rest};
json_parse_string_value([$\\, $" | Rest], Acc) ->
    json_parse_string_value(Rest, [$" | Acc]);
json_parse_string_value([$\\, $\\ | Rest], Acc) ->
    json_parse_string_value(Rest, [$\\ | Acc]);
json_parse_string_value([$\\, $t | Rest], Acc) ->
    json_parse_string_value(Rest, [$\t | Acc]);
json_parse_string_value([$\\, $n | Rest], Acc) ->
    json_parse_string_value(Rest, [$\n | Acc]);
json_parse_string_value([$\\, $r | Rest], Acc) ->
    json_parse_string_value(Rest, [$\r | Acc]);
json_parse_string_value([C | Rest], Acc) ->
    json_parse_string_value(Rest, [C | Acc]).

json_parse_value(Str) ->
    Str1 = skip_whitespace(Str),
    case Str1 of
        [$" | _] -> 
            {Value, Rest} = json_parse_string_value(Str1, []),
            {list_to_binary(Value), skip_whitespace(Rest)};
        [$t, $r, $u, $e | Rest] ->
            {true, skip_whitespace(Rest)};
        [$f, $a, $l, $s, $e | Rest] ->
            {false, skip_whitespace(Rest)};
        [$n, $u, $l, $l | Rest] ->
            {null, skip_whitespace(Rest)};
        [C | Rest] when C >= $0 andalso C =< $9; C == $- ->
            {NumStr, Rest2} = json_parse_number(Str1, []),
            {list_to_integer(lists:reverse(NumStr)), skip_whitespace(Rest2)};
        [$[ | _] ->
            {Value, Rest} = json_parse_array(Str1, []),
            {Value, skip_whitespace(Rest)};
        [${ | _] ->
            {Value, Rest} = json_parse_object(Str1, {}),
            {Value, skip_whitespace(Rest)};
        _ -> {error, invalid_value}
    end.

json_parse_number([C | Rest], Acc) when C >= $0 andalso C =< $9; C == $- ->
    json_parse_number(Rest, [C | Acc]);
json_parse_number(Rest, Acc) ->
    {Acc, Rest}.

json_parse_array([$[ | Rest], Acc) ->
    Str1 = skip_whitespace(Rest),
    case Str1 of
        [$] | Rest2] ->
            {[], skip_whitespace(Rest2)};
        _ ->
            {Value, Rest2} = json_parse_value(Str1),
            json_parse_array_items(Rest2, [Value])
    end.

json_parse_array_items(Str, Acc) ->
    Str1 = skip_whitespace(Str),
    case Str1 of
        [$, | Rest] ->
            Str2 = skip_whitespace(Rest),
            {Value, Rest2} = json_parse_value(Str2),
            json_parse_array_items(Rest2, [Value | Acc]);
        [$] | Rest] ->
            {lists:reverse(Acc), skip_whitespace(Rest)};
        _ -> {error, invalid_array}
    end.

skip_whitespace([$ | Rest]) -> skip_whitespace(Rest);
skip_whitespace([$\t | Rest]) -> skip_whitespace(Rest);
skip_whitespace([$\n | Rest]) -> skip_whitespace(Rest);
skip_whitespace([$\r | Rest]) -> skip_whitespace(Rest);
skip_whitespace(Str) -> Str.
