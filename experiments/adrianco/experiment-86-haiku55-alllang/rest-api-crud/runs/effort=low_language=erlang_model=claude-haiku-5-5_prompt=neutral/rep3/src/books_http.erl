%% Minimal HTTP/1.1 server on gen_tcp. One request per connection (Connection: close).
-module(books_http).
-behaviour(gen_server).

-export([start_link/1, port/1]).
-export([init/1, handle_call/3, handle_cast/2, handle_info/2, terminate/2]).

-define(MAX_HEAD, 16384).
-define(MAX_BODY, 1048576).
-define(RECV_TIMEOUT, 5000).

%% Port 0 picks an ephemeral port; use port/1 to find it.
start_link(Port) ->
    gen_server:start_link(?MODULE, Port, []).

port(Server) ->
    gen_server:call(Server, port).

init(Port) ->
    {ok, Listen} = gen_tcp:listen(Port, [binary, {active, false}, {reuseaddr, true}, {packet, raw}]),
    {ok, ActualPort} = inet:port(Listen),
    Acceptor = spawn_link(fun() -> accept_loop(Listen) end),
    {ok, #{listen => Listen, port => ActualPort, acceptor => Acceptor}}.

handle_call(port, _From, State) ->
    {reply, maps:get(port, State), State}.

handle_cast(_Msg, State) ->
    {noreply, State}.

handle_info(_Msg, State) ->
    {noreply, State}.

terminate(_Reason, #{listen := Listen}) ->
    gen_tcp:close(Listen),
    ok.

accept_loop(Listen) ->
    case gen_tcp:accept(Listen) of
        {ok, Socket} ->
            Pid = spawn(fun() ->
                receive {socket, Socket} -> serve(Socket) end
            end),
            ok = gen_tcp:controlling_process(Socket, Pid),
            Pid ! {socket, Socket},
            accept_loop(Listen);
        {error, _} ->
            ok
    end.

serve(Socket) ->
    Response = case read_request(Socket) of
        {ok, Method, Target, Body} -> dispatch(Method, Target, Body);
        {error, Reason} -> {400, #{<<"error">> => Reason}}
    end,
    send_response(Socket, Response),
    gen_tcp:close(Socket).

dispatch(Method, Target, Body) ->
    try
        books_handler:handle(Method, Target, Body)
    catch
        Class:Reason:Stack ->
            logger:error("request ~s ~s failed: ~p:~p ~p", [Method, Target, Class, Reason, Stack]),
            {500, #{<<"error">> => <<"internal server error">>}}
    end.

read_request(Socket) ->
    case recv_head(Socket, <<>>) of
        {ok, Head, Rest} -> parse_request(Socket, Head, Rest);
        {error, _} = Error -> Error
    end.

recv_head(Socket, Acc) ->
    case binary:match(Acc, <<"\r\n\r\n">>) of
        {Pos, 4} ->
            <<Head:Pos/binary, _:32, Rest/binary>> = Acc,
            {ok, Head, Rest};
        nomatch when byte_size(Acc) > ?MAX_HEAD ->
            {error, <<"request headers too large">>};
        nomatch ->
            case gen_tcp:recv(Socket, 0, ?RECV_TIMEOUT) of
                {ok, Data} -> recv_head(Socket, <<Acc/binary, Data/binary>>);
                {error, _} -> {error, <<"connection error">>}
            end
    end.

parse_request(Socket, Head, Rest) ->
    [RequestLine | HeaderLines] = binary:split(Head, <<"\r\n">>, [global]),
    case binary:split(RequestLine, <<" ">>, [global]) of
        [Method, Target, _Version] ->
            case content_length(parse_headers(HeaderLines)) of
                {ok, Length} ->
                    case read_body(Socket, Rest, Length) of
                        {ok, Body} -> {ok, Method, Target, Body};
                        {error, _} = Error -> Error
                    end;
                {error, _} = Error ->
                    Error
            end;
        _ ->
            {error, <<"malformed request line">>}
    end.

parse_headers(Lines) ->
    [{string:lowercase(string:trim(Name)), string:trim(Value)} ||
        Line <- Lines,
        [Name, Value] <- [binary:split(Line, <<":">>)]].

content_length(Headers) ->
    case string:to_integer(proplists:get_value(<<"content-length">>, Headers, <<"0">>)) of
        {Length, <<>>} when Length >= 0, Length =< ?MAX_BODY -> {ok, Length};
        _ -> {error, <<"invalid content-length">>}
    end.

read_body(_Socket, Buffer, Length) when byte_size(Buffer) >= Length ->
    <<Body:Length/binary, _/binary>> = Buffer,
    {ok, Body};
read_body(Socket, Buffer, Length) ->
    case gen_tcp:recv(Socket, Length - byte_size(Buffer), ?RECV_TIMEOUT) of
        {ok, Data} -> read_body(Socket, <<Buffer/binary, Data/binary>>, Length);
        {error, _} -> {error, <<"incomplete request body">>}
    end.

send_response(Socket, {Status, Term}) ->
    Body = encode_body(Term),
    Head = io_lib:format(
        "HTTP/1.1 ~B ~s\r\nContent-Type: application/json\r\nContent-Length: ~B\r\nConnection: close\r\n\r\n",
        [Status, reason(Status), byte_size(Body)]),
    gen_tcp:send(Socket, [Head, Body]).

encode_body(undefined) -> <<>>;
encode_body(Term) -> iolist_to_binary(json:encode(Term)).

reason(200) -> "OK";
reason(201) -> "Created";
reason(204) -> "No Content";
reason(400) -> "Bad Request";
reason(404) -> "Not Found";
reason(405) -> "Method Not Allowed";
reason(500) -> "Internal Server Error";
reason(_) -> "Unknown".
