-module(soccer_json).
-export([encode/1, decode/1]).

encode(M) when is_map(M) -> <<"{", (join([<<(encode_key(K))/binary, ":", (encode(V))/binary>> || {K,V} <- maps:to_list(M)]))/binary, "}">>;
encode(L) when is_list(L) -> case io_lib:printable_list(L) of true -> encode(unicode:characters_to_binary(L)); false -> <<"[",(join([encode(X)||X<-L]))/binary,"]">> end;
encode(B) when is_binary(B) -> <<$",(escape(B))/binary,$">>; encode(true)-><<"true">>; encode(false)-><<"false">>; encode(null)-><<"null">>;
encode(A) when is_atom(A) -> encode(atom_to_binary(A,utf8)); encode(I) when is_integer(I) -> integer_to_binary(I); encode(F) when is_float(F) -> float_to_binary(F,[short]).
encode_key(K) when is_atom(K)->encode(atom_to_binary(K,utf8)); encode_key(K)->encode(K).
join([])-><<>>; join([X])->X; join([X|Xs])-><<X/binary, $,, (join(Xs))/binary>>.
escape(B)->binary:replace(binary:replace(binary:replace(B, <<"\\">>, <<"\\\\">>,[global]), <<$">>, <<"\\\"">>,[global]), <<"\n">>, <<"\\n">>,[global]).

decode(Bin) when is_binary(Bin) -> try {Value, Rest}=value(skip(Bin)), case skip(Rest) of <<>> -> {ok,Value}; _ -> {error, trailing_data} end catch _:_ -> {error, invalid_json} end.
skip(<<C,Rest/binary>>) when C=:=32;C=:=9;C=:=10;C=:=13 -> skip(Rest); skip(B)->B.
value(<<$",R/binary>>)->string(R,<<>>); value(<<${,R/binary>>)->object(skip(R),#{}); value(<<$[,R/binary>>)->array(skip(R),[]); value(<<"true",R/binary>>)->{true,R}; value(<<"false",R/binary>>)->{false,R}; value(<<"null",R/binary>>)->{null,R}; value(B)->number(B,<<>>).
string(<<$",R/binary>>,A)->{A,R}; string(<<$\\,$",R/binary>>,A)->string(R,<<A/binary,$">>); string(<<$\\,$\\,R/binary>>,A)->string(R,<<A/binary,$\\>>); string(<<$\\,$n,R/binary>>,A)->string(R,<<A/binary,$\n>>); string(<<C/utf8,R/binary>>,A)->string(R,<<A/binary,C/utf8>>).
object(<<$},R/binary>>,A)->{A,R}; object(B,A)->{K,R1}=value(B), R2=skip(R1), <<$:,R3/binary>>=R2, {V,R4}=value(skip(R3)), R5=skip(R4), case R5 of <<$},R/binary>>->{maps:put(K,V,A),R}; <<$,,R/binary>>->object(skip(R),maps:put(K,V,A)) end.
array(<<$],R/binary>>,A)->{lists:reverse(A),R}; array(B,A)->{V,R1}=value(B), R2=skip(R1), case R2 of <<$],R/binary>>->{lists:reverse([V|A]),R}; <<$,,R/binary>>->array(skip(R),[V|A]) end.
number(<<C,R/binary>>,A) when (C >= $0 andalso C =< $9) orelse C=:= $- orelse C=:= $. -> number(R,<<A/binary,C>>); number(R,A)-> case binary:match(A,<<".">>) of nomatch->{binary_to_integer(A),R}; _->{binary_to_float(A),R} end.
