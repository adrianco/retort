%% Minimal HTTP/1.1 server on gen_tcp (one process per connection).
-module(books_http).
-export([start_link/1, port/0, accept_loop/1, handle_conn/1]).

start_link(Port) ->
    {ok, LSock} = gen_tcp:listen(Port, [binary, {packet, http_bin}, {active, false},
                                        {reuseaddr, true}, {backlog, 128}]),
    {ok, Bound} = inet:port(LSock),
    persistent_term:put({?MODULE, port}, Bound),
    Pid = spawn_link(?MODULE, accept_loop, [LSock]),
    ok = gen_tcp:controlling_process(LSock, Pid),
    {ok, Pid}.

%% Actual listening port (useful when configured with port 0).
port() -> persistent_term:get({?MODULE, port}).

accept_loop(LSock) ->
    {ok, Sock} = gen_tcp:accept(LSock),
    Pid = spawn(?MODULE, handle_conn, [Sock]),
    ok = gen_tcp:controlling_process(Sock, Pid),
    accept_loop(LSock).

handle_conn(Sock) ->
    case gen_tcp:recv(Sock, 0, 30000) of
        {ok, {http_request, Method, {abs_path, Path}, _Vsn}} ->
            Headers = read_headers(Sock, #{}),
            Len = binary_to_integer(maps:get('Content-Length', Headers, <<"0">>)),
            ok = inet:setopts(Sock, [{packet, raw}]),
            Body = case Len of
                       0 -> <<>>;
                       _ -> {ok, B} = gen_tcp:recv(Sock, Len, 30000), B
                   end,
            {Status, Resp} = safe_handle(method(Method), Path, Body),
            send(Sock, Status, Resp),
            Close = maps:get('Connection', Headers, <<>>) =:= <<"close">>,
            case Close of
                true -> gen_tcp:close(Sock);
                false -> ok = inet:setopts(Sock, [{packet, http_bin}]), handle_conn(Sock)
            end;
        _ -> gen_tcp:close(Sock)
    end.

read_headers(Sock, Acc) ->
    case gen_tcp:recv(Sock, 0, 30000) of
        {ok, {http_header, _, Name, _, Value}} -> read_headers(Sock, Acc#{Name => Value});
        {ok, http_eoh} -> Acc
    end.

method(M) when is_atom(M) -> atom_to_binary(M);
method(M) -> M.

safe_handle(M, P, B) ->
    try books_api:handle(M, P, B)
    catch C:E:St ->
        logger:error("request failed: ~p:~p ~p", [C, E, St]),
        {500, #{<<"error">> => <<"internal server error">>}}
    end.

send(Sock, Status, Resp) ->
    Body = case Resp of no_content -> <<>>; _ -> iolist_to_binary(json:encode(Resp)) end,
    Hdr = io_lib:format("HTTP/1.1 ~b ~s\r\nContent-Type: application/json\r\n"
                        "Content-Length: ~b\r\n\r\n", [Status, reason(Status), byte_size(Body)]),
    gen_tcp:send(Sock, [Hdr, Body]).

reason(200) -> "OK"; reason(201) -> "Created"; reason(204) -> "No Content";
reason(400) -> "Bad Request"; reason(404) -> "Not Found";
reason(405) -> "Method Not Allowed"; reason(_) -> "Internal Server Error".
