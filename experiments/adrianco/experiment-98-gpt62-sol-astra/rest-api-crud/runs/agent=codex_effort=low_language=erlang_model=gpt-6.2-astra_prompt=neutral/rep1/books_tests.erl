-module(books_tests).
-include_lib("eunit/include/eunit.hrl").
-include_lib("inets/include/httpd.hrl").

api_test_() ->
    {setup, fun setup/0, fun cleanup/1, fun({_File, Base}) ->
        [?_assertEqual({200, #{<<"status">> => <<"ok">>}}, request(get, Base ++ "/health")),
         ?_test(validation(Base)), ?_test(lifecycle(Base)), ?_test(filter(Base))]
    end}.

setup() ->
    File = filename:join(os:getenv("TMPDIR", "/tmp"),
                         "books-" ++ binary_to_list(binary:encode_hex(crypto:strong_rand_bytes(8)))),
    {ok, books_db} = dets:open_file(books_db, [{file, File}]),
    {File, ""}.

cleanup({File, _}) ->
    ok = dets:close(books_db),
    ok = file:delete(File).

request(Method, Url) -> write(Method, Url, <<>>).
write(Method, Url, Data) ->
    Request = #mod{method = string:uppercase(atom_to_list(Method)),
                   request_uri = Url, entity_body = Data},
    {proceed, [{response, {response, Headers, Body}}]} = books:do(Request),
    ?assertEqual("application/json", proplists:get_value(content_type, Headers)),
    {proplists:get_value(code, Headers), json:decode(Body)}.

validation(Base) ->
    lists:foreach(fun(Data) ->
        ?assertMatch({400, _}, write(post, Base ++ "/books", Data))
    end, ["{", "[]", "{}", "{\"author\":\"A\"}", "{\"title\":\"T\",\"author\":\"  \"}"]).

lifecycle(Base) ->
    Book = #{<<"title">> => <<"A">>, <<"author">> => <<"B">>,
             <<"year">> => 2020, <<"isbn">> => <<"012345">>},
    {201, #{<<"id">> := Id} = Created} = write(post, Base ++ "/books", json:encode(Book)),
    Url = Base ++ "/books/" ++ binary_to_list(Id),
    ?assertEqual(Book#{<<"id">> => Id}, Created),
    ?assertEqual({200, Created}, request(get, Url)),
    Updated = Book#{<<"year">> := 2021},
    Expected = {200, Updated#{<<"id">> => Id}},
    ?assertEqual(Expected, write(put, Url, json:encode(Updated))),
    ?assertEqual(Expected, request(get, Url)),
    ?assertMatch({200, _}, request(delete, Url)),
    ?assertMatch({404, _}, request(get, Url)),
    ?assertMatch({404, _}, write(put, Url, json:encode(Book))).

filter(Base) ->
    Url = Base ++ "/books",
    Add = fun(Author) ->
        {201, Book} = write(post, Url, json:encode(#{author => Author, title => <<"A">>})),
        Book
    end,
    A = Add(<<"Ann Lee">>),
    B = Add(<<"Other">>),
    {200, All} = request(get, Url),
    ?assertEqual(lists:sort([A,B]), lists:sort(All)),
    ?assertEqual({200, [A]}, request(get, Url ++ "?author=Ann%20Lee")),
    ?assertEqual({200, []}, request(get, Url ++ "?author=Nobody")).
