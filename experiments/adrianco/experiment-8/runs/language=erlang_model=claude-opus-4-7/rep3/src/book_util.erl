-module(book_util).

-export([parse_body/1, validate/1, book_to_json/1, json_reply/3, error_reply/3]).

parse_body(<<>>) ->
    {error, <<"request body is empty">>};
parse_body(Bin) when is_binary(Bin) ->
    try jsone:decode(Bin, [{object_format, map}]) of
        Map when is_map(Map) -> {ok, normalize_keys(Map)};
        _ -> {error, <<"invalid json: expected an object">>}
    catch
        _:_ -> {error, <<"invalid json">>}
    end.

normalize_keys(M) ->
    maps:fold(
      fun(K, V, Acc) ->
          Acc#{key_to_atom(K) => V}
      end, #{}, M).

key_to_atom(<<"title">>)  -> title;
key_to_atom(<<"author">>) -> author;
key_to_atom(<<"year">>)   -> year;
key_to_atom(<<"isbn">>)   -> isbn;
key_to_atom(<<"id">>)     -> id;
key_to_atom(K)            -> K.

validate(Data) when is_map(Data) ->
    case is_present(maps:get(title, Data, undefined)) of
        false -> {error, <<"title is required">>};
        true ->
            case is_present(maps:get(author, Data, undefined)) of
                false -> {error, <<"author is required">>};
                true  -> ok
            end
    end;
validate(_) ->
    {error, <<"invalid payload">>}.

is_present(undefined) -> false;
is_present(<<>>)      -> false;
is_present("")        -> false;
is_present(_)         -> true.

book_to_json(Book) ->
    #{
        id     => maps:get(id, Book),
        title  => maps:get(title, Book, null),
        author => maps:get(author, Book, null),
        year   => maps:get(year, Book, null),
        isbn   => maps:get(isbn, Book, null)
    }.

json_reply(Code, Term, Req) ->
    Body = jsone:encode(Term),
    cowboy_req:reply(
      Code,
      #{<<"content-type">> => <<"application/json">>},
      Body,
      Req).

error_reply(Code, Msg, Req) ->
    json_reply(Code, #{error => Msg}, Req).
