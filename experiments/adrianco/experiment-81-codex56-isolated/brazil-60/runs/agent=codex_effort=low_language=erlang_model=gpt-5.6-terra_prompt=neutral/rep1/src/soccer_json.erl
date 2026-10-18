-module(soccer_json).
-export([encode/1,decode/1]).
encode(T)->iolist_to_binary(enc(T)).
enc(M)when is_map(M)->[${,join([[enc(K),$:,enc(V)]||{K,V}<-maps:to_list(M)]),$}];enc(L)when is_list(L)->[$[,join([enc(X)||X<-L]),$]];enc(B)when is_binary(B)->[$",esc(B),$"];enc(true)->"true";enc(false)->"false";enc(null)->"null";enc(A)when is_atom(A)->enc(atom_to_binary(A));enc(I)when is_integer(I)->integer_to_list(I);enc(F)when is_float(F)->float_to_binary(F,[short]).
join([])->[];join([X])->X;join([X|Xs])->[X,$,,join(Xs)].
esc(<<>>)->[];esc(<<$",R/binary>>)->["\\\""|esc(R)];esc(<<$\\,R/binary>>)->["\\\\"|esc(R)];esc(<<10,R/binary>>)->["\\n"|esc(R)];esc(<<C/utf8,R/binary>>)->[C|esc(R)].
decode(B)->try {V,R}=val(skip(B)),case skip(R)of <<>>->{ok,V};_->{error,<<"trailing JSON">>}end catch _:_->{error,<<"invalid JSON">>}end.
val(<<$",R/binary>>)->str(R,<<>>);val(<<${,R/binary>>)->obj(skip(R),#{});val(<<$[,R/binary>>)->arr(skip(R),[]);val(<<"true",R/binary>>)->{true,R};val(<<"false",R/binary>>)->{false,R};val(<<"null",R/binary>>)->{null,R};val(B)->num(B).
str(<<$",R/binary>>,A)->{A,R};str(<<$\\,$",R/binary>>,A)->str(R,<<A/binary,$">>);str(<<$\\,$n,R/binary>>,A)->str(R,<<A/binary,10>>);str(<<C/utf8,R/binary>>,A)->str(R,<<A/binary,C/utf8>>).
obj(<<$},R/binary>>,M)->{M,R};obj(B,M)->{K,R1}=val(B),<<$:,R2/binary>>=skip(R1),{V,R3}=val(skip(R2)),case skip(R3)of <<$},R4/binary>>->{maps:put(K,V,M),R4};<<$,,R4/binary>>->obj(skip(R4),maps:put(K,V,M))end.
arr(<<$],R/binary>>,A)->{lists:reverse(A),R};arr(B,A)->{V,R}=val(B),case skip(R)of <<$],R2/binary>>->{lists:reverse([V|A]),R2};<<$,,R2/binary>>->arr(skip(R2),[V|A])end.
num(B)->{T,R}=take(B,<<>>),case binary:match(T,<<".">>)of nomatch->{binary_to_integer(T),R};_->{binary_to_float(T),R}end.
take(<<C,R/binary>>,A)when(C>=$0 andalso C=<$9)orelse C=:= $- orelse C=:= $.->take(R,<<A/binary,C>>);take(R,A)->{A,R}.
skip(<<C,R/binary>>)when C=:=32;C=:=10;C=:=13;C=:=9->skip(R);skip(B)->B.
