-module(books_json).
-export([decode/1, encode_book/1, encode_books/1, encode_error/1, encode_ok/0]).

decode(Bin) when is_binary(Bin) ->
    try
        {Value, Rest} = value(skip(Bin)),
        case skip(Rest) of <<>> when is_map(Value) -> {ok, Value}; _ -> {error, invalid_json} end
    catch _:_ -> {error, invalid_json} end.

encode_book(B) -> iolist_to_binary(["{\"id\":", integer_to_binary(maps:get(id, B)), ",\"title\":", string(maps:get(title, B)), ",\"author\":", string(maps:get(author, B)), ",\"year\":", nullable(maps:get(year, B, null)), ",\"isbn\":", nullable(maps:get(isbn, B, null)), "}"]).
encode_books(Books) -> iolist_to_binary(["[", lists:join(",", [encode_book(B) || B <- Books]), "]"]).
encode_error(Message) -> iolist_to_binary(["{\"error\":", string(Message), "}"]).
encode_ok() -> <<"{\"status\":\"ok\"}">>.

nullable(null) -> "null"; nullable(undefined) -> "null"; nullable(V) when is_integer(V) -> integer_to_binary(V); nullable(V) -> string(V).
string(V) when is_binary(V) -> [$", escape(V), $"]; string(V) when is_list(V) -> string(unicode:characters_to_binary(V)).
escape(<<>>) -> <<>>;
escape(<<$", R/binary>>) -> ["\\\"", escape(R)]; escape(<<$\\, R/binary>>) -> ["\\\\", escape(R)];
escape(<<$\n, R/binary>>) -> ["\\n", escape(R)]; escape(<<C/utf8, R/binary>>) -> [<<C/utf8>>, escape(R)].

skip(<<C, R/binary>>) when C =:= $\s; C =:= $\n; C =:= $\r; C =:= $\t -> skip(R); skip(B) -> B.
value(<<$", R/binary>>) -> str(R, <<>>);
value(<<${, R/binary>>) -> object(skip(R), #{});
value(<<"null", R/binary>>) -> {null, R};
value(B) -> number(B, <<>>).
str(<<$", R/binary>>, Acc) -> {Acc, R};
str(<<$\\, $", R/binary>>, Acc) -> str(R, <<Acc/binary, $">>); str(<<$\\, $\\, R/binary>>, Acc) -> str(R, <<Acc/binary, $\\>>);
str(<<$\\, $n, R/binary>>, Acc) -> str(R, <<Acc/binary, $\n>>); str(<<C/utf8, R/binary>>, Acc) -> str(R, <<Acc/binary, C/utf8>>).
object(<<$}, R/binary>>, Acc) -> {Acc, R};
object(<<$", R/binary>>, Acc) -> {Key, AfterKey} = str(R, <<>>), Colon = skip(AfterKey), <<$:, ValueStart/binary>> = Colon, {Val, AfterVal} = value(skip(ValueStart)), Next = skip(AfterVal), case Next of <<$,, More/binary>> -> object(skip(More), Acc#{Key => Val}); <<$}, Rest/binary>> -> {Acc#{Key => Val}, Rest} end.
number(<<C, R/binary>>, Acc) when C >= $0, C =< $9 -> number(R, <<Acc/binary, C>>); number(Rest, Acc) when byte_size(Acc) > 0 -> {binary_to_integer(Acc), Rest}.
