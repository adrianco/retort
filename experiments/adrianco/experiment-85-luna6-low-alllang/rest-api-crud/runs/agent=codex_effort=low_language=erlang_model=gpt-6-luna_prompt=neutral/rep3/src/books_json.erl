-module(books_json).

-export([decode/1, encode/1]).

decode(Data) when is_binary(Data) -> decode(binary_to_list(Data));
decode(Data) when is_list(Data) ->
    try
        {Value, Rest} = value(skip_ws(Data)),
        case skip_ws(Rest) of
            [] -> {ok, Value};
            _ -> {error, trailing_data}
        end
    catch
        throw:Reason -> {error, Reason};
        error:_ -> {error, invalid_json}
    end.

encode(Value) -> iolist_to_binary(enc(Value)).

value([${ | Rest]) -> object(skip_ws(Rest), #{});
value([$[ | Rest]) -> array(skip_ws(Rest), []);
value([$" | Rest]) ->
    {Decoded, Tail} = string(Rest, []),
    {unicode:characters_to_binary(Decoded), Tail};
value([$t,$r,$u,$e | Rest]) -> {true, Rest};
value([$f,$a,$l,$s,$e | Rest]) -> {false, Rest};
value([$n,$u,$l,$l | Rest]) -> {null, Rest};
value(List) -> number(List).

object([$} | Rest], Acc) -> {Acc, Rest};
object([$" | Rest], Acc) ->
    {KeyChars, AfterKey} = string(Rest, []),
    Key = unicode:characters_to_binary(KeyChars),
    case skip_ws(AfterKey) of
        [$: | AfterColon] ->
            {Val, AfterVal} = value(skip_ws(AfterColon)),
            case skip_ws(AfterVal) of
                [$, | More] -> object(skip_ws(More), maps:put(Key, Val, Acc));
                [$} | More] -> {maps:put(Key, Val, Acc), More};
                _ -> throw(invalid_object)
            end;
        _ -> throw(invalid_object)
    end;
object(_, _) -> throw(invalid_object).

array([$] | Rest], Acc) -> {lists:reverse(Acc), Rest};
array(List, Acc) ->
    {Val, AfterVal} = value(List),
    case skip_ws(AfterVal) of
        [$, | More] -> array(skip_ws(More), [Val | Acc]);
        [$] | More] -> {lists:reverse([Val | Acc]), More};
        _ -> throw(invalid_array)
    end.

string([$" | Rest], Acc) -> {lists:reverse(Acc), Rest};
string([$\\, $" | Rest], Acc) -> string(Rest, [$" | Acc]);
string([$\\, $\\ | Rest], Acc) -> string(Rest, [$\\ | Acc]);
string([$\\, $/ | Rest], Acc) -> string(Rest, [$/ | Acc]);
string([$\\, $b | Rest], Acc) -> string(Rest, [8 | Acc]);
string([$\\, $f | Rest], Acc) -> string(Rest, [12 | Acc]);
string([$\\, $n | Rest], Acc) -> string(Rest, [10 | Acc]);
string([$\\, $r | Rest], Acc) -> string(Rest, [13 | Acc]);
string([$\\, $t | Rest], Acc) -> string(Rest, [9 | Acc]);
string([$\\, $u, A, B, C, D | Rest], Acc) ->
    try list_to_integer([A,B,C,D], 16) of
        Code -> string(Rest, [Code | Acc])
    catch _:_ -> throw(invalid_escape) end;
string([C | Rest], Acc) when C >= 32 -> string(Rest, [C | Acc]);
string(_, _) -> throw(invalid_string).

number(List) ->
    {Token, Rest} = take_number(List, []),
    case Token of
        [] -> throw(invalid_value);
        _ ->
            try {list_to_integer(Token), Rest}
            catch _:_ ->
                try {list_to_float(normalize_float(Token)), Rest}
                catch _:_ -> throw(invalid_number) end
            end
    end.

take_number([C | Rest], Acc)
  when (C >= $0 andalso C =< $9) orelse C =:= $- orelse C =:= $+ orelse
       C =:= $. orelse C =:= $e orelse C =:= $E -> take_number(Rest, [C | Acc]);
take_number(Rest, Acc) -> {lists:reverse(Acc), Rest}.

normalize_float(Token) ->
    case lists:member($., Token) of
        true -> Token;
        false -> case lists:member($e, Token) orelse lists:member($E, Token) of
                     true -> Token;
                     false -> Token ++ ".0"
                 end
    end.

skip_ws([C | Rest]) when C =:= 32; C =:= 9; C =:= 10; C =:= 13 -> skip_ws(Rest);
skip_ws(Rest) -> Rest.

enc(null) -> "null";
enc(true) -> "true";
enc(false) -> "false";
enc(N) when is_integer(N) -> integer_to_list(N);
enc(N) when is_float(N) -> io_lib:format("~p", [N]);
enc(B) when is_binary(B) -> enc(binary_to_list(B));
enc(S) when is_list(S) -> [$\" | [escape(C) || C <- S]] ++ [$\"];
enc(M) when is_map(M) ->
    Pairs = [[enc_key(K), $:, enc(V)] || {K, V} <- maps:to_list(M)],
    [${, join(Pairs, $,), $}];
enc(_) -> "null".

enc_key(K) when is_atom(K) -> enc(atom_to_list(K));
enc_key(K) when is_binary(K) -> enc(binary_to_list(K));
enc_key(K) -> enc(K).

escape($\") -> "\\\"";
escape($\\) -> "\\\\";
escape(8) -> "\\b";
escape(12) -> "\\f";
escape(10) -> "\\n";
escape(13) -> "\\r";
escape(9) -> "\\t";
escape(C) when C < 32 -> io_lib:format("\\u~4.16.0B", [C]);
escape(C) -> C.

join([], _) -> [];
join([One], _) -> One;
join([One | Rest], Sep) -> [One, Sep | join(Rest, Sep)].
