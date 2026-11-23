-module(book_api_tests).

-include_lib("eunit/include/eunit.hrl").
-include_lib("inets/include/httpd.hrl").

health_test() ->
    with_api(fun(Base, _Db) ->
        {200, Headers, #{<<"status">> := <<"ok">>}} = request(get, Base, "/health"),
        ?assertEqual("application/json", proplists:get_value("content-type", Headers)),
        {404, _, #{<<"error">> := _}} = request(get, Base, "/other"),
        {405, MethodHeaders, #{<<"error">> := _}} = request(delete, Base, "/books"),
        ?assertEqual("GET, POST", proplists:get_value("allow", MethodHeaders))
    end).

crud_test() ->
    with_api(fun(Base, _Db) ->
        {200, _, []} = request(get, Base, "/books"),
        Fields = #{<<"title">> => <<"Kindred">>, <<"author">> => <<"Octavia Butler">>,
                   <<"year">> => 1979, <<"isbn">> => <<"9780807083697">>},
        {201, Headers, #{<<"id">> := Id} = Created} = request(post, Base, "/books", Fields),
        Path = "/books/" ++ integer_to_list(Id),
        ?assertEqual(Path, proplists:get_value("location", Headers)),
        ?assertEqual(Fields#{<<"id">> => Id}, Created),
        {200, _, [Created]} = request(get, Base, "/books"),
        {200, _, Created} = request(get, Base, Path),
        Update = Fields#{<<"title">> => <<"Wild Seed">>, <<"year">> => 1980},
        Updated = Update#{<<"id">> => Id},
        {200, _, Updated} = request(put, Base, Path, Update),
        {200, _, Updated} = request(get, Base, Path),
        {204, _, <<>>} = request(delete, Base, Path),
        {404, _, #{<<"error">> := _}} = request(get, Base, Path),
        {404, _, #{<<"error">> := _}} = request(put, Base, Path, Update),
        {404, _, #{<<"error">> := _}} = request(delete, Base, Path),
        {200, _, []} = request(get, Base, "/books")
    end).

author_filter_test() ->
    with_api(fun(Base, _Db) ->
        {201, _, Book} = request(post, Base, "/books",
                                #{<<"title">> => <<"Ficciones">>,
                                  <<"author">> => <<"Jorge Luis Borges">>}),
        {201, _, Other} = request(post, Base, "/books",
                                 #{<<"title">> => <<"Beloved">>,
                                   <<"author">> => <<"Toni Morrison">>}),
        {200, _, [Book, Other]} = request(get, Base, "/books"),
        {200, _, [Book]} = request(get, Base, "/books?author=Jorge+Luis%20Borges"),
        {200, _, []} = request(get, Base, "/books?author=Borges")
    end).

validation_test() ->
    with_api(fun(Base, _Db) ->
        Title = #{<<"title">> => <<"The Book">>},
        Author = #{<<"author">> => <<"An Author">>},
        Valid = maps:merge(Title, Author),
        Invalid = [Title, Author, Valid#{<<"title">> => <<"  ">>},
                   Valid#{<<"author">> => 42}, Valid#{<<"year">> => <<"1980">>},
                   Valid#{<<"isbn">> => 123}, <<"[]">>, <<"{">>],
        lists:foreach(fun(Body) ->
            {400, _, #{<<"error">> := _}} = request(post, Base, "/books", Body)
        end, Invalid),
        {200, _, []} = request(get, Base, "/books"),
        {201, _, Book} = request(post, Base, "/books", Valid),
        Path = "/books/" ++ integer_to_list(maps:get(<<"id">>, Book)),
        {400, _, #{<<"error">> := _}} = request(put, Base, Path, Title),
        {200, _, Book} = request(get, Base, Path)
    end).

persistence_test() ->
    with_database(fun(Db) ->
        Fields = #{<<"title">> => <<"Persuasion">>, <<"author">> => <<"Jane Austen">>},
        Book = with_server(Db, fun(Base) ->
            {201, _, Created} = request(post, Base, "/books", Fields),
            Created
        end),
        Id = maps:get(<<"id">>, Book),
        with_server(Db, fun(Base) ->
            {200, _, [Book]} = request(get, Base, "/books"),
            {204, _, <<>>} = request(delete, Base, "/books/" ++ integer_to_list(Id))
        end),
        with_server(Db, fun(Base) ->
            {200, _, []} = request(get, Base, "/books"),
            {201, _, #{<<"id">> := NewId}} = request(post, Base, "/books", Fields),
            ?assert(NewId > Id)
        end)
    end).

with_api(Test) ->
    with_database(fun(Db) ->
        with_server(Db, fun(Base) -> Test(Base, Db) end)
    end).

with_database(Test) ->
    Tmp = os:getenv("TMPDIR", "/tmp"),
    Name = "book-api-" ++ os:getpid() ++ "-" ++ integer_to_list(erlang:unique_integer([positive])),
    Dir = filename:join(Tmp, Name),
    ok = file:make_dir(Dir),
    try Test(filename:join(Dir, "books.dets"))
    after
        ok = file:del_dir_r(Dir)
    end.

with_server(Db, Test) ->
    case os:getenv("BOOK_API_HTTP_TEST") of
        "1" -> with_http_server(Db, Test);
        _ ->
            {ok, _} = book_store:start_link(Db),
            try Test(callback)
            after
                ok = book_store:stop()
            end
    end.

with_http_server(Db, Test) ->
    {ok, Server} = book_api:start(0, Db),
    try
        Port = proplists:get_value(port, httpd:info(Server)),
        Test("http://127.0.0.1:" ++ integer_to_list(Port))
    after
        ok = book_api:stop(Server)
    end.

request(Method, callback, Path) ->
    request(Method, callback, Path, <<>>);
request(Method, Base, Path) ->
    send(Method, {Base ++ Path, []}).

request(Method, callback, Path, Body) ->
    Request = #mod{method = string:uppercase(atom_to_list(Method)),
                   request_uri = Path, entity_body = binary_to_list(encode(Body))},
    {proceed, [{response, {response, Headers, Payload}}]} = book_api:do(Request),
    Status = proplists:get_value(code, Headers),
    WireHeaders = [{"content-type", Value} || {content_type, Value} <- Headers]
        ++ [{Key, Value} || {Key, Value} <- Headers, is_list(Key)],
    {Status, WireHeaders, decode(Payload)};
request(Method, Base, Path, Body) ->
    send(Method, {Base ++ Path, [], "application/json", encode(Body)}).

encode(Body) when is_binary(Body) -> Body;
encode(Body) -> iolist_to_binary(json:encode(Body)).

send(Method, Request) ->
    {ok, {{_, Status, _}, Headers, Body}} =
        httpc:request(Method, Request, [{timeout, 3000}], [{body_format, binary}]),
    {Status, Headers, decode(Body)}.

decode(<<>>) -> <<>>;
decode(Body) -> json:decode(Body).
