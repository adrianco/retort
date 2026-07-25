%%%-------------------------------------------------------------------
%%% @doc Shared request/response plumbing for the Cowboy handlers:
%%% JSON encoding, body decoding and the canonical error envelope.
%%%
%%% Every error response has the same shape, so clients can rely on it:
%%% ```
%%% {"error": "not_found", "message": "Book 42 does not exist"}
%%% {"error": "validation_failed", "message": "...",
%%%  "details": [{"field": "title", "message": "is required"}]}
%%% '''
%%% @end
%%%-------------------------------------------------------------------
-module(book_api_http).

-export([json/3, error/4, error/5, method_not_allowed/2, read_json_body/1,
         parse_id/1, handle/2]).

-define(MAX_BODY_BYTES, 1048576). %% 1 MiB is ample for a book record.

%%%===================================================================
%%% Responses
%%%===================================================================

%% @doc Send `Body' (any term `json:encode/1' accepts) as a JSON response.
-spec json(cowboy:http_status(), term(), cowboy_req:req()) -> cowboy_req:req().
json(Status, Body, Req) ->
    cowboy_req:reply(Status,
                     #{<<"content-type">> => <<"application/json">>},
                     json:encode(Body),
                     Req).

-spec error(cowboy:http_status(), binary(), iodata(), cowboy_req:req()) ->
          cowboy_req:req().
error(Status, Code, Message, Req) ->
    json(Status, error_body(Code, Message), Req).

-spec error(cowboy:http_status(), binary(), iodata(), book:errors(),
            cowboy_req:req()) -> cowboy_req:req().
error(Status, Code, Message, Details, Req) ->
    Body = (error_body(Code, Message))#{<<"details">> => Details},
    json(Status, Body, Req).

-spec method_not_allowed([binary()], cowboy_req:req()) -> cowboy_req:req().
method_not_allowed(Allowed, Req0) ->
    Req = cowboy_req:set_resp_header(<<"allow">>, lists:join(", ", Allowed), Req0),
    ?MODULE:error(405, <<"method_not_allowed">>,
                  [<<"Method not allowed; try ">>, lists:join(", ", Allowed)],
                  Req).

error_body(Code, Message) ->
    #{<<"error">> => Code, <<"message">> => iolist_to_binary(Message)}.

%%%===================================================================
%%% Requests
%%%===================================================================

%% @doc Read the request body and decode it as JSON.
-spec read_json_body(cowboy_req:req()) ->
          {ok, term(), cowboy_req:req()} | {error, cowboy_req:req()}.
read_json_body(Req0) ->
    case read_body(Req0, <<>>) of
        {ok, <<>>, Req} ->
            {error, ?MODULE:error(400, <<"invalid_json">>,
                                  <<"Request body must not be empty">>, Req)};
        {ok, Raw, Req} ->
            try json:decode(Raw) of
                Decoded -> {ok, Decoded, Req}
            catch
                _:_ ->
                    {error, ?MODULE:error(400, <<"invalid_json">>,
                                          <<"Request body is not valid JSON">>, Req)}
            end;
        {too_large, Req} ->
            {error, ?MODULE:error(413, <<"payload_too_large">>,
                                  <<"Request body exceeds 1 MiB">>, Req)}
    end.

%% The limit has to be enforced against the accumulated total after every
%% read: Cowboy happily hands back a multi-megabyte body in a single `ok'
%% chunk, so checking only on re-entry would never fire.
read_body(Req0, Acc) ->
    case cowboy_req:read_body(Req0, #{length => ?MAX_BODY_BYTES + 1}) of
        {ok, Chunk, Req} -> check_size(<<Acc/binary, Chunk/binary>>, Req, done);
        {more, Chunk, Req} -> check_size(<<Acc/binary, Chunk/binary>>, Req, more)
    end.

check_size(Acc, Req, _More) when byte_size(Acc) > ?MAX_BODY_BYTES ->
    {too_large, Req};
check_size(Acc, Req, done) ->
    {ok, Acc, Req};
check_size(Acc, Req, more) ->
    read_body(Req, Acc).

%% @doc Parse the `:id' path binding. Anything that is not a positive
%% integer cannot name an existing book, so it is reported as not found.
-spec parse_id(binary()) -> {ok, pos_integer()} | error.
parse_id(Bin) ->
    try binary_to_integer(Bin) of
        Id when Id > 0 -> {ok, Id};
        _NonPositive -> error
    catch
        error:badarg -> error
    end.

%% @doc Run a handler body, converting any unexpected crash into a 500
%% JSON response instead of Cowboy's empty default error page.
-spec handle(fun(() -> cowboy_req:req()), cowboy_req:req()) -> cowboy_req:req().
handle(Fun, Req) ->
    try
        Fun()
    catch
        Class:Reason:Stack ->
            logger:error("book_api request failed: ~p:~p~n~p",
                         [Class, Reason, Stack]),
            ?MODULE:error(500, <<"internal_error">>,
                          <<"The server failed to process the request">>, Req)
    end.
