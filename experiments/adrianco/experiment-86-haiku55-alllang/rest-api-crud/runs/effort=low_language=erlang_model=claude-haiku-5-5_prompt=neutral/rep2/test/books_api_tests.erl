%% End-to-end tests: start the application on an ephemeral port and call it over HTTP.
-module(books_api_tests).
-include_lib("eunit/include/eunit.hrl").

-define(DB, "books_api_test.dets").

api_test_() ->
    {foreach, fun start/0, fun stop/1, [
        fun health_returns_ok/1,
        fun create_and_get_book/1,
        fun create_rejects_missing_title/1,
        fun create_rejects_invalid_json/1,
        fun list_filters_by_author/1,
        fun update_book/1,
        fun delete_book/1,
        fun unknown_or_invalid_id_returns_404/1
    ]}.

start() ->
    {ok, _} = application:ensure_all_started(inets),
    file:delete(?DB),
    application:load(books),
    application:set_env(books, port, 0),
    application:set_env(books, db_file, ?DB),
    {ok, _} = application:ensure_all_started(books),
    Port = ranch:get_port(books_http),
    "http://localhost:" ++ integer_to_list(Port).

stop(_Base) ->
    ok = application:stop(books),
    file:delete(?DB),
    ok.

health_returns_ok(Base) ->
    fun() ->
        ?assertMatch({200, _, #{<<"status">> := <<"ok">>}}, request(get, Base ++ "/health"))
    end.

create_and_get_book(Base) ->
    fun() ->
        {201, Headers, Created} = request(post, Base ++ "/books", dune()),
        ?assertMatch(#{<<"id">> := 1, <<"title">> := <<"Dune">>, <<"year">> := 1965}, Created),
        ?assertEqual("/books/1", proplists:get_value("location", Headers)),
        ?assertEqual({200, Created}, get_book(Base, 1))
    end.

create_rejects_missing_title(Base) ->
    fun() ->
        Body = json:encode(#{<<"author">> => <<"Frank Herbert">>}),
        ?assertMatch({400, _, #{<<"error">> := <<"validation failed">>,
                                <<"details">> := [<<"title is required">>]}},
                     request(post, Base ++ "/books", Body))
    end.

create_rejects_invalid_json(Base) ->
    fun() ->
        ?assertMatch({400, _, #{<<"error">> := <<"request body must be valid JSON">>}},
                     request(post, Base ++ "/books", <<"{not json">>))
    end.

list_filters_by_author(Base) ->
    fun() ->
        request(post, Base ++ "/books", dune()),
        request(post, Base ++ "/books",
                json:encode(#{<<"title">> => <<"Foundation">>, <<"author">> => <<"Isaac Asimov">>})),
        {200, _, All} = request(get, Base ++ "/books"),
        ?assertEqual(2, length(All)),
        {200, _, Filtered} = request(get, Base ++ "/books?author=Isaac%20Asimov"),
        ?assertEqual([<<"Foundation">>], [T || #{<<"title">> := T} <- Filtered])
    end.

update_book(Base) ->
    fun() ->
        request(post, Base ++ "/books", dune()),
        Body = json:encode(#{<<"title">> => <<"Dune Messiah">>, <<"author">> => <<"Frank Herbert">>}),
        ?assertMatch({200, _, #{<<"id">> := 1, <<"title">> := <<"Dune Messiah">>}},
                     request(put, Base ++ "/books/1", Body)),
        ?assertMatch({200, #{<<"title">> := <<"Dune Messiah">>}}, get_book(Base, 1)),
        ?assertMatch({404, _, _}, request(put, Base ++ "/books/99", Body))
    end.

delete_book(Base) ->
    fun() ->
        request(post, Base ++ "/books", dune()),
        ?assertMatch({204, _, _}, request(delete, Base ++ "/books/1")),
        ?assertEqual({404, #{<<"error">> => <<"book not found">>}}, get_book(Base, 1)),
        ?assertMatch({404, _, _}, request(delete, Base ++ "/books/1"))
    end.

unknown_or_invalid_id_returns_404(Base) ->
    fun() ->
        ?assertMatch({404, _, _}, request(get, Base ++ "/books/999")),
        ?assertMatch({404, _, _}, request(get, Base ++ "/books/abc")),
        ?assertMatch({404, _, _}, request(get, Base ++ "/books/0"))
    end.

%% Helpers

dune() ->
    json:encode(#{<<"title">> => <<"Dune">>, <<"author">> => <<"Frank Herbert">>,
                  <<"year">> => 1965, <<"isbn">> => <<"9780441172719">>}).

get_book(Base, Id) ->
    case request(get, Base ++ "/books/" ++ integer_to_list(Id)) of
        {Status, _, Body} -> {Status, Body}
    end.

%% Returns {Status, Headers, DecodedJsonBody}; the body is kept raw when it
%% is not JSON (e.g. empty 204 responses).
request(Method, Url) ->
    send(httpc:request(Method, {Url, []}, [], [{body_format, binary}])).

request(Method, Url, Body) ->
    send(httpc:request(Method, {Url, [], "application/json", iolist_to_binary(Body)},
                       [], [{body_format, binary}])).

send({ok, {{_, Status, _}, Headers, Body}}) ->
    Decoded = case Body of
        <<>> -> <<>>;
        _ -> json:decode(Body)
    end,
    {Status, Headers, Decoded}.
