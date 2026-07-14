%%% @doc Maps HTTP requests onto book operations. Pure with respect to the
%%% socket: it takes the parsed request and returns `{StatusCode, BodyMap}'.
-module(booklib_router).

-export([route/4]).

%% @doc Dispatch a request. `Method' and `Path' are binaries, `Query' is the
%% raw query string, and `Body' is the raw request body.
-spec route(binary(), binary(), binary(), binary()) -> {integer(), map()}.
route(Method, Path, Query, Body) ->
    Segments = path_segments(Path),
    handle(Method, Segments, Query, Body).

%% --- Health check ---------------------------------------------------
handle(<<"GET">>, [<<"health">>], _Query, _Body) ->
    {200, #{<<"status">> => <<"ok">>}};

%% --- Collection: /books ---------------------------------------------
handle(<<"GET">>, [<<"books">>], Query, _Body) ->
    Author = query_param(<<"author">>, Query),
    Books = booklib_db:list(Author),
    {200, #{<<"books">> => Books, <<"count">> => length(Books)}};

handle(<<"POST">>, [<<"books">>], _Query, Body) ->
    with_json(Body, fun(Attrs) ->
        case booklib_db:create(Attrs) of
            {ok, Book} ->
                {201, Book};
            {error, {validation, Errors}} ->
                validation_response(Errors)
        end
    end);

%% --- Member: /books/:id ---------------------------------------------
handle(<<"GET">>, [<<"books">>, IdBin], _Query, _Body) ->
    with_id(IdBin, fun(Id) ->
        case booklib_db:get(Id) of
            {ok, Book} -> {200, Book};
            {error, not_found} -> not_found()
        end
    end);

handle(<<"PUT">>, [<<"books">>, IdBin], _Query, Body) ->
    with_id(IdBin, fun(Id) ->
        with_json(Body, fun(Attrs) ->
            case booklib_db:update(Id, Attrs) of
                {ok, Book} -> {200, Book};
                {error, not_found} -> not_found();
                {error, {validation, Errors}} -> validation_response(Errors)
            end
        end)
    end);

handle(<<"DELETE">>, [<<"books">>, IdBin], _Query, _Body) ->
    with_id(IdBin, fun(Id) ->
        case booklib_db:delete(Id) of
            ok -> {200, #{<<"deleted">> => Id}};
            {error, not_found} -> not_found()
        end
    end);

%% --- Method not allowed on known resources --------------------------
handle(_Method, [<<"books">>], _Query, _Body) ->
    method_not_allowed();
handle(_Method, [<<"books">>, _Id], _Query, _Body) ->
    method_not_allowed();
handle(_Method, [<<"health">>], _Query, _Body) ->
    method_not_allowed();

%% --- Fallthrough ----------------------------------------------------
handle(_Method, _Segments, _Query, _Body) ->
    not_found().

%%====================================================================
%% Helpers
%%====================================================================

with_json(Body, Fun) ->
    case decode_json(Body) of
        {ok, Map} when is_map(Map) ->
            Fun(Map);
        {ok, _NotAnObject} ->
            {400, #{<<"error">> => <<"request body must be a JSON object">>}};
        {error, _} ->
            {400, #{<<"error">> => <<"invalid JSON in request body">>}}
    end.

decode_json(Body) ->
    try {ok, json:decode(Body)}
    catch _:_ -> {error, invalid_json}
    end.

with_id(IdBin, Fun) ->
    try
        Id = binary_to_integer(IdBin),
        case Id > 0 of
            true -> Fun(Id);
            false -> {400, #{<<"error">> => <<"id must be a positive integer">>}}
        end
    catch
        error:badarg ->
            {400, #{<<"error">> => <<"id must be a positive integer">>}}
    end.

validation_response(Errors) ->
    {422, #{<<"error">> => <<"validation failed">>, <<"details">> => Errors}}.

not_found() ->
    {404, #{<<"error">> => <<"not found">>}}.

method_not_allowed() ->
    {405, #{<<"error">> => <<"method not allowed">>}}.

path_segments(Path) ->
    [S || S <- binary:split(Path, <<"/">>, [global]), S =/= <<>>].

%% Extract and percent-decode a single query parameter value.
query_param(_Name, <<>>) ->
    undefined;
query_param(Name, Query) ->
    Pairs = binary:split(Query, <<"&">>, [global]),
    find_param(Name, Pairs).

find_param(_Name, []) ->
    undefined;
find_param(Name, [Pair | Rest]) ->
    case binary:split(Pair, <<"=">>) of
        [Name, Value] -> url_decode(Value);
        _ -> find_param(Name, Rest)
    end.

%% Minimal application/x-www-form-urlencoded decoding ('+' -> space, %XX).
url_decode(Bin) ->
    url_decode(Bin, <<>>).

url_decode(<<>>, Acc) ->
    Acc;
url_decode(<<$+, Rest/binary>>, Acc) ->
    url_decode(Rest, <<Acc/binary, $\s>>);
url_decode(<<$%, H, L, Rest/binary>>, Acc) ->
    case {hex(H), hex(L)} of
        {Hi, Lo} when is_integer(Hi), is_integer(Lo) ->
            url_decode(Rest, <<Acc/binary, (Hi * 16 + Lo)>>);
        _ ->
            url_decode(Rest, <<Acc/binary, $%, H, L>>)
    end;
url_decode(<<C, Rest/binary>>, Acc) ->
    url_decode(Rest, <<Acc/binary, C>>).

hex(C) when C >= $0, C =< $9 -> C - $0;
hex(C) when C >= $a, C =< $f -> C - $a + 10;
hex(C) when C >= $A, C =< $F -> C - $A + 10;
hex(_) -> invalid.
