-module(soccer_json).
-export([encode/1]).

encode(Term) -> iolist_to_binary(value(Term)).
value(M) when is_map(M) -> [${, join([[string(key(K)), $:, value(V)] || {K,V} <- maps:to_list(M)]), $}];
value(L) when is_list(L), L =/= [], is_integer(hd(L)) -> string(L);
value(L) when is_list(L) -> [$[, join([value(V) || V <- L]), $]];
value(B) when is_binary(B) -> string(unicode:characters_to_list(B));
value(A) when is_atom(A) -> string(atom_to_list(A));
value(I) when is_integer(I) -> integer_to_list(I);
value(F) when is_float(F) -> io_lib:format("~.4f", [F]);
value(true) -> "true"; value(false) -> "false"; value(undefined) -> "null".
key(K) when is_atom(K)->atom_to_list(K); key(K)->K.
string(S) -> [$" | escape(S)] ++ [$"].
escape([])->[]; escape([$"|T])->"\\\""++escape(T); escape([$\\|T])->"\\\\"++escape(T); escape([$\n|T])->"\\n"++escape(T); escape([$\r|T])->"\\r"++escape(T); escape([$\t|T])->"\\t"++escape(T); escape([C|T]) when C < 32 -> io_lib:format("\\u~4.16.0B",[C]) ++ escape(T); escape([C|T])->[C|escape(T)].
join([])->[]; join([H])->H; join([H|T])->[H,$,|join(T)].
