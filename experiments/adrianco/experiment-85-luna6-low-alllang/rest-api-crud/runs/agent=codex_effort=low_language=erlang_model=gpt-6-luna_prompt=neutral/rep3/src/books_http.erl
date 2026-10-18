-module(books_http).
-behaviour(gen_server).

-export([start_link/1, request/4]).
-export([init/1, handle_call/3, handle_cast/2, handle_info/2, terminate/2, code_change/3]).

-record(state, {listen}).

start_link(Port) -> gen_server:start_link({local, ?MODULE}, ?MODULE, Port, []).

init(Port) ->
    case gen_tcp:listen(Port, [binary, {packet, raw}, {active, false}, {reuseaddr, true}, {backlog, 128}]) of
        {ok, Listen} -> self() ! accept, {ok, #state{listen = Listen}};
        {error, Reason} -> {stop, {listen_failed, Reason}}
    end.

handle_call(_Request, _From, State) -> {reply, {error, bad_request}, State}.
handle_cast(_Msg, State) -> {noreply, State}.
handle_info(accept, State = #state{listen = Listen}) ->
    case gen_tcp:accept(Listen) of
        {ok, Socket} ->
            spawn(fun() -> serve(Socket) end),
            self() ! accept,
            {noreply, State};
        {error, closed} -> {stop, normal, State};
        {error, _Reason} -> self() ! accept, {noreply, State}
    end;
handle_info(_Info, State) -> {noreply, State}.

terminate(_Reason, #state{listen = Listen}) -> gen_tcp:close(Listen), ok.
code_change(_Old, State, _Extra) -> {ok, State}.

serve(Socket) ->
    case read_request(Socket) of
        {ok, Method, Target, Headers, Body} ->
            {Status, Response} = request(Method, Target, Headers, Body),
            send_response(Socket, Status, Response);
        {error, _} -> send_response(Socket, 400, #{error => <<"Bad Request">>})
    end,
    gen_tcp:close(Socket).

read_request(Socket) ->
    case recv_until(Socket, <<"\r\n\r\n">>, <<>>, 10000) of
        {ok, HeaderBin, Rest} ->
            case binary:split(HeaderBin, <<"\r\n">>, [global]) of
                [RequestLine | HeaderLines] ->
                    case binary:split(RequestLine, <<" ">>, [global]) of
                        [Method, Target, _Version] ->
                            Headers = parse_headers(HeaderLines),
                            Length = case maps:get(<<"content-length">>, Headers, <<"0">>) of
                                         V -> try binary_to_integer(V) catch _:_ -> 0 end
                                     end,
                            case read_body(Socket, Rest, Length) of
                                {ok, Body} -> {ok, Method, Target, Headers, Body};
                                Error -> Error
                            end;
                        _ -> {error, invalid_request_line}
                    end;
                _ -> {error, missing_request_line}
            end;
        Error -> Error
    end.

recv_until(Socket, Needle, Acc, Timeout) ->
    case binary:match(Acc, Needle) of
        {Pos, Len} ->
            Head = binary:part(Acc, 0, Pos),
            RestStart = Pos + Len,
            Rest = binary:part(Acc, RestStart, byte_size(Acc) - RestStart),
            {ok, Head, Rest};
        nomatch ->
            case gen_tcp:recv(Socket, 0, Timeout) of
                {ok, Data} -> recv_until(Socket, Needle, <<Acc/binary, Data/binary>>, Timeout);
                Error -> Error
            end
    end.

read_body(_Socket, Rest, Length) when byte_size(Rest) >= Length ->
    {ok, binary:part(Rest, 0, Length)};
read_body(Socket, Rest, Length) ->
    case gen_tcp:recv(Socket, Length - byte_size(Rest), 10000) of
        {ok, Data} -> read_body(Socket, <<Rest/binary, Data/binary>>, Length);
        Error -> Error
    end.

parse_headers(Lines) ->
    lists:foldl(fun(Line, Acc) ->
        case binary:split(Line, <<":">>) of
            [Key, Value] -> maps:put(lower(binary:trim(Key, both, <<" ">>)), binary:trim(Value, both, <<" ">>), Acc);
            _ -> Acc
        end
    end, #{}, Lines).

request(<<"GET">>, <<"/health">>, _Headers, _Body) -> {200, #{status => <<"ok">>}};
request(Method, Target, _Headers, Body) ->
    {Path, Query} = split_target(Target),
    case {Method, path_segments(Path)} of
        {<<"POST">>, [<<"books">>]} ->
            with_valid_book(Body, fun(Book) ->
                case books_store:create(Book) of {ok, Created} -> {201, Created}; Error -> storage_error(Error) end
            end);
        {<<"GET">>, [<<"books">>]} ->
            Author = query_author(Query),
            case books_store:list(Author) of {ok, Books} -> {200, Books}; Error -> storage_error(Error) end;
        {<<"GET">>, [<<"books">>, IdText]} ->
            with_id(IdText, fun(Id) -> case books_store:get(Id) of {ok, Book} -> {200, Book}; Error -> storage_error(Error) end end);
        {<<"PUT">>, [<<"books">>, IdText]} ->
            with_id(IdText, fun(Id) -> with_valid_book(Body, fun(Book) ->
                case books_store:update(Id, Book) of {ok, Updated} -> {200, Updated}; Error -> storage_error(Error) end
            end) end);
        {<<"DELETE">>, [<<"books">>, IdText]} ->
            with_id(IdText, fun(Id) -> case books_store:delete(Id) of {ok, deleted} -> {204, <<>>}; Error -> storage_error(Error) end end);
        _ -> {404, #{error => <<"Not Found">>}}
    end.

with_valid_book(Body, Fun) ->
    case books_json:decode(Body) of
        {ok, Book} when is_map(Book) ->
            case required(Book) of
                ok -> Fun(Book);
                {error, Message} -> {400, #{error => Message}}
            end;
        _ -> {400, #{error => <<"Invalid JSON object">>}}
    end.

required(Book) ->
    case {maps:get(<<"title">>, Book, undefined), maps:get(<<"author">>, Book, undefined)} of
        {Title, Author} when is_binary(Title), byte_size(Title) > 0, is_binary(Author), byte_size(Author) > 0 -> ok;
        _ -> {error, <<"title and author are required">>}
    end.

with_id(IdText, Fun) ->
    try binary_to_integer(IdText) of
        Id when Id > 0 -> Fun(Id);
        _ -> {400, #{error => <<"Invalid book id">>}}
    catch _:_ -> {400, #{error => <<"Invalid book id">>}}
    end.

storage_error({error, not_found}) -> {404, #{error => <<"Book not found">>}};
storage_error(Error) -> {500, #{error => iolist_to_binary(io_lib:format("Storage error: ~p", [Error]))}}.

split_target(Target) ->
    case binary:split(Target, <<"?">>) of [Path, Query] -> {Path, Query}; [Path] -> {Path, <<>>} end.

path_segments(Path) -> [percent_decode(S) || S <- binary:split(Path, <<"/">>, [global]), S =/= <<>>].

query_author(<<>>) -> undefined;
query_author(Query) ->
    Pairs = [binary:split(Pair, <<"=">>) || Pair <- binary:split(Query, <<"&">>, [global])],
    case lists:keyfind(<<"author">>, 1, [case P of [K,V] -> {K,V}; [K] -> {K,<<>>} end || P <- Pairs]) of
        {_, Value} -> percent_decode(Value);
        false -> undefined
    end.

percent_decode(Bin) -> percent_decode(Bin, <<>>).
percent_decode(<<$%, A, B, Rest/binary>>, Acc) ->
    try binary_to_integer(<<A,B>>, 16) of C -> percent_decode(Rest, <<Acc/binary, C>>) catch _:_ -> percent_decode(Rest, <<Acc/binary, $%, A, B>>) end;
percent_decode(<<$+, Rest/binary>>, Acc) -> percent_decode(Rest, <<Acc/binary, $ >>);
percent_decode(<<C, Rest/binary>>, Acc) -> percent_decode(Rest, <<Acc/binary, C>>);
percent_decode(<<>>, Acc) -> Acc.

lower(Bin) -> list_to_binary(string:lowercase(binary_to_list(Bin))).

send_response(Socket, Status, Body) ->
    Payload = case Body of <<>> -> <<>>; _ -> books_json:encode(Body) end,
    Reason = reason(Status),
    Response = ["HTTP/1.1 ", integer_to_list(Status), " ", Reason, "\r\n",
                "Content-Type: application/json; charset=utf-8\r\n",
                "Content-Length: ", integer_to_list(byte_size(Payload)), "\r\n",
                "Connection: close\r\n\r\n", Payload],
    gen_tcp:send(Socket, Response).

reason(200) -> "OK";
reason(201) -> "Created";
reason(204) -> "No Content";
reason(400) -> "Bad Request";
reason(404) -> "Not Found";
reason(500) -> "Internal Server Error";
reason(_) -> "Error".
