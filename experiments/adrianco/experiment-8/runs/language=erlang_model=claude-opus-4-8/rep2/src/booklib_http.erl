%%% @doc HTTP connection handling: read and parse a single request, dispatch it
%%% to the router, and write the response. One request per connection
%%% (Connection: close) keeps the implementation small and predictable.
-module(booklib_http).

-export([handle_connection/1]).

-define(RECV_TIMEOUT, 30000).
-define(MAX_BODY, 1048576). %% 1 MiB cap on request bodies

%%====================================================================
%% Connection handling
%%====================================================================

handle_connection(Socket) ->
    Result =
        try
            case read_request(Socket) of
                {ok, Method, Path, Query, Body} ->
                    booklib_router:route(Method, Path, Query, Body);
                {error, body_too_large} ->
                    {413, #{<<"error">> => <<"request body too large">>}};
                {error, _Reason} ->
                    {400, #{<<"error">> => <<"bad request">>}}
            end
        catch
            Class:Error:Stack ->
                error_logger:error_msg("request failed: ~p:~p~n~p~n",
                                       [Class, Error, Stack]),
                {500, #{<<"error">> => <<"internal server error">>}}
        end,
    {Status, BodyMap} = Result,
    send_response(Socket, Status, BodyMap),
    gen_tcp:close(Socket).

%%====================================================================
%% Request parsing
%%====================================================================

read_request(Socket) ->
    case read_headers(Socket, <<>>) of
        {ok, HeaderBin, Rest} ->
            [RequestLine | HeaderLines] = binary:split(HeaderBin, <<"\r\n">>, [global]),
            case parse_request_line(RequestLine) of
                {ok, Method, RawPath} ->
                    Headers = parse_headers(HeaderLines),
                    {Path, Query} = split_path(RawPath),
                    case read_body(Socket, Headers, Rest) of
                        {ok, Body} ->
                            {ok, Method, Path, Query, Body};
                        {error, _} = Err ->
                            Err
                    end;
                {error, _} = Err ->
                    Err
            end;
        {error, _} = Err ->
            Err
    end.

%% Accumulate bytes until the end-of-headers marker is found.
read_headers(Socket, Acc) ->
    case binary:match(Acc, <<"\r\n\r\n">>) of
        {Pos, _Len} ->
            <<HeaderBin:Pos/binary, "\r\n\r\n", Rest/binary>> = Acc,
            {ok, HeaderBin, Rest};
        nomatch when byte_size(Acc) > ?MAX_BODY ->
            {error, headers_too_large};
        nomatch ->
            case gen_tcp:recv(Socket, 0, ?RECV_TIMEOUT) of
                {ok, Data} -> read_headers(Socket, <<Acc/binary, Data/binary>>);
                {error, Reason} -> {error, Reason}
            end
    end.

parse_request_line(Line) ->
    case binary:split(Line, <<" ">>, [global]) of
        [Method, RawPath | _Version] ->
            {ok, Method, RawPath};
        _ ->
            {error, malformed_request_line}
    end.

parse_headers(Lines) ->
    lists:foldl(fun(<<>>, Acc) -> Acc;
                   (Line, Acc) ->
                        case binary:split(Line, <<":">>) of
                            [Name, Value] ->
                                Key = string:lowercase(string:trim(Name)),
                                [{Key, string:trim(Value)} | Acc];
                            _ ->
                                Acc
                        end
                end, [], Lines).

read_body(Socket, Headers, Rest) ->
    case content_length(Headers) of
        {ok, 0} ->
            {ok, <<>>};
        {ok, Length} when Length > ?MAX_BODY ->
            {error, body_too_large};
        {ok, Length} ->
            recv_body(Socket, Length, Rest);
        error ->
            %% No Content-Length: treat whatever arrived with the headers as
            %% the body (typically empty for our supported methods).
            {ok, Rest}
    end.

recv_body(_Socket, Length, Acc) when byte_size(Acc) >= Length ->
    <<Body:Length/binary, _/binary>> = Acc,
    {ok, Body};
recv_body(Socket, Length, Acc) ->
    case gen_tcp:recv(Socket, 0, ?RECV_TIMEOUT) of
        {ok, Data} -> recv_body(Socket, Length, <<Acc/binary, Data/binary>>);
        {error, Reason} -> {error, Reason}
    end.

content_length(Headers) ->
    case lists:keyfind(<<"content-length">>, 1, Headers) of
        {_, Value} ->
            try {ok, binary_to_integer(string:trim(Value))}
            catch _:_ -> error
            end;
        false ->
            error
    end.

split_path(RawPath) ->
    case binary:split(RawPath, <<"?">>) of
        [Path] -> {Path, <<>>};
        [Path, Query] -> {Path, Query}
    end.

%%====================================================================
%% Response writing
%%====================================================================

send_response(Socket, Status, BodyMap) ->
    Body = json:encode(BodyMap),
    Reason = reason_phrase(Status),
    Headers = [
        <<"HTTP/1.1 ">>, integer_to_binary(Status), <<" ">>, Reason, <<"\r\n">>,
        <<"Content-Type: application/json\r\n">>,
        <<"Content-Length: ">>, integer_to_binary(iolist_size(Body)), <<"\r\n">>,
        <<"Connection: close\r\n">>,
        <<"\r\n">>
    ],
    gen_tcp:send(Socket, [Headers, Body]).

reason_phrase(200) -> <<"OK">>;
reason_phrase(201) -> <<"Created">>;
reason_phrase(204) -> <<"No Content">>;
reason_phrase(400) -> <<"Bad Request">>;
reason_phrase(404) -> <<"Not Found">>;
reason_phrase(405) -> <<"Method Not Allowed">>;
reason_phrase(413) -> <<"Payload Too Large">>;
reason_phrase(422) -> <<"Unprocessable Entity">>;
reason_phrase(500) -> <<"Internal Server Error">>;
reason_phrase(_)   -> <<"OK">>.
