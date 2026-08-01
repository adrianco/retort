-module(books_http).
-behaviour(gen_server).
-export([start_link/1, port/0, route/4]).
-export([init/1, handle_call/3, handle_cast/2, handle_info/2, terminate/2, code_change/3]).

start_link(Port) -> gen_server:start_link({local, ?MODULE}, ?MODULE, [Port], []).
port() -> gen_server:call(?MODULE, port).
init([Port]) -> {ok, Listen} = gen_tcp:listen(Port, [binary, {packet, raw}, {active, false}, {reuseaddr, true}]), self() ! accept, {ok, #{listen => Listen}}.
handle_call(port, _, State=#{listen := L}) -> {ok, {ok, Port}} = inet:sockname(L), {reply, Port, State};
handle_call(_, _, State) -> {reply, ok, State}.
handle_cast(_, State) -> {noreply, State}.
handle_info(accept, State=#{listen := L}) -> case gen_tcp:accept(L) of {ok, Socket} -> spawn(fun() -> serve(Socket) end); _ -> ok end, self() ! accept, {noreply, State};
handle_info(_, State) -> {noreply, State}.
terminate(_, #{listen := L}) -> gen_tcp:close(L), ok.
code_change(_, State, _) -> {ok, State}.

serve(Socket) ->
    case read_request(Socket, <<>>) of
        {ok, Method, Target, Headers, Body} -> {Status, Resp} = route(Method, Target, Headers, Body), send(Socket, Status, Resp);
        _ -> send(Socket, 400, books_json:encode_error(<<"bad request">>))
    end, gen_tcp:close(Socket).
read_request(S, Acc) ->
    case binary:match(Acc, <<"\r\n\r\n">>) of
        {Pos, 4} -> <<Head:Pos/binary, _/binary>> = Acc, [Line | HLines] = binary:split(Head, <<"\r\n">>, [global]), [M, T, _] = binary:split(Line, <<" ">>, [global]), H = headers(HLines, #{}), Need = maps:get(<<"content-length">>, H, 0), Have = byte_size(Acc) - Pos - 4, if Have >= Need -> <<_:Pos/binary, _Sep:4/binary, Body:Need/binary, _/binary>> = Acc, {ok, M, T, H, Body}; true -> recv(S, Acc) end;
        nomatch -> recv(S, Acc)
    end.
recv(S, Acc) -> case gen_tcp:recv(S, 0, 5000) of {ok, B} -> read_request(S, <<Acc/binary, B/binary>>); Error -> Error end.
headers([], Acc) -> Acc;
headers([Line | Rest], Acc) ->
    case binary:split(Line, <<":">>) of
        [K, V] ->
            Key = lower(K), Value = trim(V),
            Stored = case Key of <<"content-length">> -> binary_to_integer(Value); _ -> Value end,
            headers(Rest, Acc#{Key => Stored});
        _ -> headers(Rest, Acc)
    end.
lower(B) -> unicode:characters_to_binary(string:lowercase(binary_to_list(B))).
trim(B) -> unicode:characters_to_binary(string:trim(binary_to_list(B))).

route(<<"GET">>, <<"/health">>, _, _) -> {200, books_json:encode_ok()};
route(<<"GET">>, Target, _, _) -> case split_target(Target) of {<<"/books">>, Query} -> {ok, Bs} = books_store:list(query_author(Query)), {200, books_json:encode_books(Bs)}; {Path, _} -> with_id(Path, fun(Id) -> result(books_store:get(Id), 200) end) end;
route(<<"POST">>, <<"/books">>, _, Body) -> with_book(Body, fun(B) -> result(books_store:create(B), 201) end);
route(<<"PUT">>, Path, _, Body) -> with_id(Path, fun(Id) -> with_book(Body, fun(B) -> result(books_store:update(Id, B), 200) end) end);
route(<<"DELETE">>, Path, _, _) -> with_id(Path, fun(Id) -> case books_store:delete(Id) of ok -> {204, <<>>}; not_found -> error_not_found() end end);
route(_, _, _, _) -> {404, books_json:encode_error(<<"not found">>)}.
split_target(T) -> case binary:split(T, <<"?">>) of [P,Q] -> {P,Q}; [P] -> {P,<<>>} end.
query_author(<<>>) -> undefined; query_author(Q) -> case binary:split(Q, <<"=">>) of [<<"author">>, V] -> uri_decode(V); _ -> undefined end.
uri_decode(B) -> binary:replace(B, <<"+">>, <<" ">>, [global]).
with_id(<<"/books/", Id/binary>>, Fun) -> try Fun(binary_to_integer(Id)) catch _:_ -> {400, books_json:encode_error(<<"invalid book id">>)} end;
with_id(_, _) -> {404, books_json:encode_error(<<"not found">>)}.
with_book(Body, Fun) -> case books_json:decode(Body) of {ok, B} -> case valid(B) of true -> Fun(allowed(B)); false -> {400, books_json:encode_error(<<"title and author are required">>)} end; _ -> {400, books_json:encode_error(<<"invalid JSON">>)} end.
valid(B) -> nonempty(maps:get(<<"title">>, B, undefined)) andalso nonempty(maps:get(<<"author">>, B, undefined)).
nonempty(V) when is_binary(V) -> byte_size(V) > 0; nonempty(_) -> false.
allowed(B) -> maps:from_list([{K, maps:get(atom_to_binary(K), B)} || K <- [title, author, year, isbn], maps:is_key(atom_to_binary(K), B)]).
result({ok, B}, Code) -> {Code, books_json:encode_book(B)}; result(not_found, _) -> error_not_found().
error_not_found() -> {404, books_json:encode_error(<<"book not found">>)}.
send(S, Code, Body) -> Reason = case Code of 200 -> "OK"; 201 -> "Created"; 204 -> "No Content"; 400 -> "Bad Request"; 404 -> "Not Found" end, gen_tcp:send(S, ["HTTP/1.1 ", integer_to_list(Code), " ", Reason, "\r\nContent-Type: application/json\r\nContent-Length: ", integer_to_list(byte_size(Body)), "\r\nConnection: close\r\n\r\n", Body]).
