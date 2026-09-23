%% Minimal HTTP/1.1 server on gen_tcp (no external deps).
-module(books_http).
-export([start_link/1, init/1, port/0]).

%% Actual listening port (useful when configured with port 0).
port() -> persistent_term:get({?MODULE, port}).

start_link(Port) -> proc_lib:start_link(?MODULE, init, [Port]).

init(Port) ->
    {ok, L} = gen_tcp:listen(Port, [binary, {packet, http_bin}, {active, false},
                                    {reuseaddr, true}]),
    {ok, P} = inet:port(L),
    persistent_term:put({?MODULE, port}, P),
    proc_lib:init_ack({ok, self()}),
    accept(L).

accept(L) ->
    {ok, S} = gen_tcp:accept(L),
    Pid = spawn(fun() -> receive go -> conn(S) end end),
    ok = gen_tcp:controlling_process(S, Pid),
    Pid ! go,
    accept(L).

conn(S) ->
    case gen_tcp:recv(S, 0, 30000) of
        {ok, {http_request, Method, {abs_path, Uri}, _}} ->
            {Headers, Len, Close} = headers(S, [], 0, false),
            inet:setopts(S, [{packet, raw}]),
            Body = case Len of 0 -> <<>>; _ -> {ok, B} = gen_tcp:recv(S, Len, 30000), B end,
            {Path, Query} = split_uri(Uri),
            {Status, Resp} = try books_api:handle(method(Method), Path, Query, Body)
                             catch _:_ -> {500, #{<<"error">> => <<"internal error">>}} end,
            _ = Headers,
            send(S, Status, Resp, Close),
            case Close of
                true -> gen_tcp:close(S);
                false -> inet:setopts(S, [{packet, http_bin}]), conn(S)
            end;
        _ -> gen_tcp:close(S)
    end.

headers(S, Acc, Len, Close) ->
    case gen_tcp:recv(S, 0, 30000) of
        {ok, {http_header, _, 'Content-Length', _, V}} ->
            headers(S, Acc, binary_to_integer(V), Close);
        {ok, {http_header, _, 'Connection', _, V}} ->
            headers(S, Acc, Len, string:lowercase(V) =:= <<"close">>);
        {ok, {http_header, _, K, _, V}} -> headers(S, [{K, V} | Acc], Len, Close);
        {ok, http_eoh} -> {Acc, Len, Close};
        _ -> exit(normal)
    end.

method(M) when is_atom(M) -> atom_to_binary(M);
method(M) -> M.

split_uri(Uri) ->
    case binary:split(Uri, <<"?">>) of
        [P] -> {P, #{}};
        [P, Q] -> {P, maps:from_list([{K, V} || {K, V} <- uri_string:dissect_query(Q), is_binary(V)])}
    end.

send(S, Status, Resp, Close) ->
    Body = case Resp of no_content -> <<>>; _ -> iolist_to_binary(json:encode(Resp)) end,
    Conn = case Close of true -> <<"close">>; false -> <<"keep-alive">> end,
    gen_tcp:send(S, [<<"HTTP/1.1 ">>, integer_to_binary(Status), <<" ">>, reason(Status),
                     <<"\r\nContent-Type: application/json\r\nContent-Length: ">>,
                     integer_to_binary(byte_size(Body)), <<"\r\nConnection: ">>, Conn,
                     <<"\r\n\r\n">>, Body]).

reason(200) -> <<"OK">>; reason(201) -> <<"Created">>; reason(204) -> <<"No Content">>;
reason(400) -> <<"Bad Request">>; reason(404) -> <<"Not Found">>;
reason(405) -> <<"Method Not Allowed">>; reason(_) -> <<"Internal Server Error">>.
