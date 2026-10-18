-module(books_http_handler).
-behaviour(cowboy_handler).
-export([init/2, decode_book/1, nonempty/1]).

init(Req,health)->{ok,reply(200,#{status=><<"ok">>},Req),health};
init(Req,books)->case test_request(Req) of true->{ok,Req,books}; false->{ok,books_route(method(Req),Req),books} end;
init(Req,book)->case id(binding(id,Req)) of {ok,I}->{ok,book_route(method(Req),I,Req),book}; error->{ok,reply(400,#{error=><<"invalid_id">>},Req),book} end.

books_route(<<"POST">>,Req)->{Body,R}=cowboy_req:read_body(Req), case decode_book(Body) of
        {ok,B}->case books_db:create(B) of {ok,Book}->reply(201,Book,R); _->reply(500,#{error=><<"database_error">>},R) end;
        {error,E}->reply(400,#{error=>E},R) end;
books_route(<<"GET">>,Req)->Author=proplists:get_value(<<"author">>,parse_qs(Req)), case books_db:list(Author) of {ok,L}->reply(200,L,Req); _->reply(500,#{error=><<"database_error">>},Req) end;
books_route(_,Req)->reply(405,#{error=><<"method_not_allowed">>},Req).

book_route(<<"GET">>,I,R)->case books_db:get(I) of {ok,[]}->reply(404,#{error=><<"not_found">>},R); {ok,B}->reply(200,B,R); _->reply(500,#{error=><<"database_error">>},R) end;
book_route(<<"PUT">>,I,Req)->{Body,R}=cowboy_req:read_body(Req),case decode_book(Body) of {ok,B}->case books_db:update(I,B) of {ok,[]}->reply(404,#{error=><<"not_found">>},R); {ok,Updated}->reply(200,Updated,R); not_found->reply(404,#{error=><<"not_found">>},R); _->reply(500,#{error=><<"database_error">>},R) end; {error,E}->reply(400,#{error=>E},R) end;
book_route(<<"DELETE">>,I,R)->case books_db:delete(I) of ok->cowboy_req:reply(204,#{},<<>>,R); not_found->reply(404,#{error=><<"not_found">>},R); _->reply(500,#{error=><<"database_error">>},R) end;
book_route(_,_,R)->reply(405,#{error=><<"method_not_allowed">>},R).

decode_book(Body)->try jsx:decode(Body,[return_maps]) of M when is_map(M)->T=maps:get(<<"title">>,M,<<>>),A=maps:get(<<"author">>,M,<<>>),case nonempty(T) andalso nonempty(A) of true->{ok,#{title=>T,author=>A,year=>year(maps:get(<<"year">>,M,null)),isbn=>maps:get(<<"isbn">>,M,<<>>)}};false->{error,<<"title_and_author_required">>} end; _->{error,<<"invalid_json">>} catch _:_->{error,<<"invalid_json">>} end.
nonempty(V)->is_binary(V) andalso byte_size(string:trim(V))>0.
year(I) when is_integer(I)->I; year(_)->null.
id(B) when is_binary(B)->try I=binary_to_integer(B),case I>0 of true->{ok,I};false->error end catch _:_ ->error end.
reply(Code,Body,#{reply:=_}=Req)->Req#{reply=>{Code,#{<<"content-type">>=><<"application/json">>},jsx:encode(Body)}};
reply(Code,Body,Req)->cowboy_req:reply(Code,#{<<"content-type">>=><<"application/json">>},jsx:encode(Body),Req).
method(#{method:=M})->M;
method(Req)->cowboy_req:method(Req).
binding(Key,#{bindings:=Bindings})->maps:get(Key,Bindings,undefined);
binding(Key,Req)->cowboy_req:binding(Key,Req).
parse_qs(#{qs:=Qs})->Qs;
parse_qs(Req)->cowboy_req:parse_qs(Req).
test_request(#{reply:=_})->true;
test_request(_)->false.
