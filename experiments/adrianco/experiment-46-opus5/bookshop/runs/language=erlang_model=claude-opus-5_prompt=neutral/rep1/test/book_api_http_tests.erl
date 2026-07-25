%%%-------------------------------------------------------------------
%%% @doc End-to-end tests: the real application is started on an ephemeral
%%% port and driven over HTTP with `httpc', so routing, status codes,
%%% headers, JSON encoding and persistence are all exercised together.
%%% @end
%%%-------------------------------------------------------------------
-module(book_api_http_tests).

-include_lib("eunit/include/eunit.hrl").

-import(book_api_test_helper, [post/2, put/3, delete/1]).

-define(DUNE, #{<<"title">> => <<"Dune">>,
                <<"author">> => <<"Frank Herbert">>,
                <<"year">> => 1965,
                <<"isbn">> => <<"978-0-441-01359-3">>}).

api_test_() ->
    {setup,
     fun() -> book_api_test_helper:start_app(?MODULE) end,
     fun book_api_test_helper:stop_app/1,
     {inorder,
      [{foreach,
        fun book_api_test_helper:reset_db/0,
        fun(_) -> ok end,
        [{"GET /health reports the service and database as up",
          fun health/0},
         {"POST /books creates a book and returns 201 + Location",
          fun create/0},
         {"POST /books rejects a payload missing required fields",
          fun create_validation/0},
         {"POST /books rejects a malformed or empty body",
          fun create_bad_json/0},
         {"POST /books defaults the optional fields to null",
          fun create_minimal/0},
         {"POST /books round-trips non-ASCII text unchanged",
          fun create_unicode/0},
         {"POST /books refuses a body larger than the 1 MiB limit",
          fun create_oversized_body/0},
         {"GET /books lists books in insertion order",
          fun list/0},
         {"GET /books?author= filters case-insensitively",
          fun list_filtered/0},
         {"GET /books/{id} returns one book, or 404",
          fun show/0},
         {"PUT /books/{id} replaces a book",
          fun update/0},
         {"PUT /books/{id} validates and 404s like create",
          fun update_errors/0},
         {"DELETE /books/{id} returns 204 and really removes it",
          fun delete_book/0},
         {"unknown routes and methods return JSON errors",
          fun routing_errors/0}]}]}}.

%%%===================================================================
%%% Health
%%%===================================================================

health() ->
    #{status := Status, body := Body} = book_api_test_helper:get("/health"),
    ?assertEqual(200, Status),
    ?assertMatch(#{<<"status">> := <<"ok">>, <<"database">> := <<"ok">>}, Body),
    ?assertEqual(0, maps:get(<<"books">>, Body)).

%%%===================================================================
%%% Create
%%%===================================================================

create() ->
    #{status := Status, headers := Headers, body := Body} = post("/books", ?DUNE),
    ?assertEqual(201, Status),
    ?assertEqual("application/json", proplists:get_value("content-type", Headers)),
    ?assertMatch(#{<<"title">> := <<"Dune">>,
                   <<"author">> := <<"Frank Herbert">>,
                   <<"year">> := 1965,
                   <<"isbn">> := <<"978-0-441-01359-3">>}, Body),
    Id = maps:get(<<"id">>, Body),
    ?assert(is_integer(Id)),
    ?assertEqual("/books/" ++ integer_to_list(Id),
                 proplists:get_value("location", Headers)),
    %% The Location header points at something that actually resolves.
    #{status := 200, body := Fetched} =
        book_api_test_helper:get("/books/" ++ integer_to_list(Id)),
    ?assertEqual(Body, Fetched).

create_validation() ->
    #{status := Status, body := Body} = post("/books", #{<<"year">> => 1965}),
    ?assertEqual(400, Status),
    ?assertMatch(#{<<"error">> := <<"validation_failed">>}, Body),
    Details = [{maps:get(<<"field">>, D), maps:get(<<"message">>, D)}
               || D <- maps:get(<<"details">>, Body)],
    ?assertEqual([{<<"title">>, <<"is required">>},
                  {<<"author">>, <<"is required">>}], Details),
    %% Nothing was persisted.
    ?assertMatch(#{body := []}, book_api_test_helper:get("/books")).

create_bad_json() ->
    ?assertMatch(#{status := 400, body := #{<<"error">> := <<"invalid_json">>}},
                 post("/books", <<"{not json">>)),
    ?assertMatch(#{status := 400, body := #{<<"error">> := <<"invalid_json">>}},
                 post("/books", <<>>)),
    %% Valid JSON, but not an object.
    ?assertMatch(#{status := 400, body := #{<<"error">> := <<"validation_failed">>}},
                 post("/books", <<"[1,2,3]">>)).

create_minimal() ->
    Payload = #{<<"title">> => <<"Ulysses">>, <<"author">> => <<"James Joyce">>},
    #{status := 201, body := Body} = post("/books", Payload),
    ?assertMatch(#{<<"year">> := null, <<"isbn">> := null}, Body),
    ?assert(maps:is_key(<<"created_at">>, Body)).

create_unicode() ->
    Title = <<"Los detectives salvajes — 侦探"/utf8>>,
    Author = <<"Roberto Bolaño"/utf8>>,
    #{status := 201, body := Created} =
        post("/books", #{<<"title">> => Title, <<"author">> => Author}),
    ?assertEqual(Title, maps:get(<<"title">>, Created)),
    Id = maps:get(<<"id">>, Created),
    ?assertMatch(#{body := #{<<"author">> := Author}},
                 book_api_test_helper:get(path(Id))),
    %% ...including through the query-string filter.
    #{body := Found} =
        book_api_test_helper:get("/books", [{<<"author">>, Author}]),
    ?assertEqual([Title], titles(Found)).

%% The payload is otherwise perfectly valid, so a 400 here would mean the
%% size limit was never reached and validation caught it instead.
create_oversized_body() ->
    Padding = binary:copy(<<"x">>, 1024 * 1024 + 1),
    Payload = #{<<"title">> => <<"T">>, <<"author">> => <<"A">>,
                <<"note">> => Padding},
    ?assertMatch(#{status := 413,
                   body := #{<<"error">> := <<"payload_too_large">>}},
                 post("/books", Payload)),
    ?assertMatch(#{body := []}, book_api_test_helper:get("/books")).

%%%===================================================================
%%% List
%%%===================================================================

list() ->
    ?assertMatch(#{status := 200, body := []}, book_api_test_helper:get("/books")),
    [create_book(T, <<"Anon">>) || T <- [<<"One">>, <<"Two">>, <<"Three">>]],
    #{status := 200, body := Body} = book_api_test_helper:get("/books"),
    ?assertEqual([<<"One">>, <<"Two">>, <<"Three">>],
                 [maps:get(<<"title">>, B) || B <- Body]),
    ?assertEqual([1, 2, 3], [maps:get(<<"id">>, B) || B <- Body]).

list_filtered() ->
    create_book(<<"Left Hand">>, <<"Ursula K. Le Guin">>),
    create_book(<<"Dune">>, <<"Frank Herbert">>),
    create_book(<<"Dispossessed">>, <<"ursula k. le guin">>),

    #{status := 200, body := Matching} =
        book_api_test_helper:get("/books", [{"author", "URSULA K. LE GUIN"}]),
    ?assertEqual([<<"Left Hand">>, <<"Dispossessed">>], titles(Matching)),

    #{body := None} = book_api_test_helper:get("/books", [{"author", "Nobody"}]),
    ?assertEqual([], None),

    %% A blank filter is treated as "no filter" rather than "no matches".
    #{body := All} = book_api_test_helper:get("/books", [{"author", ""}]),
    ?assertEqual(3, length(All)).

%%%===================================================================
%%% Show
%%%===================================================================

show() ->
    Id = create_book(<<"Dune">>, <<"Frank Herbert">>),
    ?assertMatch(#{status := 200, body := #{<<"title">> := <<"Dune">>}},
                 book_api_test_helper:get(path(Id))),
    ?assertMatch(#{status := 404, body := #{<<"error">> := <<"not_found">>}},
                 book_api_test_helper:get("/books/999999")),
    %% Non-numeric ids cannot name a book either.
    ?assertMatch(#{status := 404, body := #{<<"error">> := <<"not_found">>}},
                 book_api_test_helper:get("/books/not-an-id")).

%%%===================================================================
%%% Update
%%%===================================================================

update() ->
    Id = create_book(<<"Dune">>, <<"Frank Herbert">>),
    Payload = #{<<"title">> => <<"Dune Messiah">>,
                <<"author">> => <<"F. Herbert">>,
                <<"year">> => 1969},
    #{status := Status, body := Body} = put(path(Id), "application/json", Payload),
    ?assertEqual(200, Status),
    ?assertMatch(#{<<"title">> := <<"Dune Messiah">>,
                   <<"author">> := <<"F. Herbert">>,
                   <<"year">> := 1969}, Body),
    ?assertEqual(Id, maps:get(<<"id">>, Body)),
    %% PUT replaces: the omitted isbn is cleared, not carried over.
    ?assertEqual(null, maps:get(<<"isbn">>, Body)),
    ?assertMatch(#{body := #{<<"title">> := <<"Dune Messiah">>}},
                 book_api_test_helper:get(path(Id))),
    %% Still exactly one book — update must not create a second row.
    ?assertMatch(#{body := [_]}, book_api_test_helper:get("/books")).

update_errors() ->
    Id = create_book(<<"Dune">>, <<"Frank Herbert">>),
    ?assertMatch(#{status := 400, body := #{<<"error">> := <<"validation_failed">>}},
                 put(path(Id), "application/json", #{<<"author">> => <<"X">>})),
    ?assertMatch(#{status := 404, body := #{<<"error">> := <<"not_found">>}},
                 put("/books/999999", "application/json", ?DUNE)),
    %% The failed update left the original untouched.
    ?assertMatch(#{body := #{<<"title">> := <<"Dune">>}},
                 book_api_test_helper:get(path(Id))).

%%%===================================================================
%%% Delete
%%%===================================================================

delete_book() ->
    Id = create_book(<<"Dune">>, <<"Frank Herbert">>),
    #{status := Status, body := Body} = delete(path(Id)),
    ?assertEqual(204, Status),
    ?assertEqual(no_content, Body),
    ?assertMatch(#{status := 404}, book_api_test_helper:get(path(Id))),
    ?assertMatch(#{status := 404}, delete(path(Id))),
    ?assertMatch(#{body := []}, book_api_test_helper:get("/books")).

%%%===================================================================
%%% Routing
%%%===================================================================

routing_errors() ->
    ?assertMatch(#{status := 404, body := #{<<"error">> := <<"not_found">>}},
                 book_api_test_helper:get("/nope")),
    #{status := Status, headers := Headers, body := Body} = delete("/books"),
    ?assertEqual(405, Status),
    ?assertMatch(#{<<"error">> := <<"method_not_allowed">>}, Body),
    ?assertEqual("GET, HEAD, POST", proplists:get_value("allow", Headers)),
    ?assertMatch(#{status := 405}, post("/health", <<"{}">>)).

%%%===================================================================
%%% Helpers
%%%===================================================================

create_book(Title, Author) ->
    #{status := 201, body := Body} =
        post("/books", #{<<"title">> => Title, <<"author">> => Author}),
    maps:get(<<"id">>, Body).

path(Id) ->
    "/books/" ++ integer_to_list(Id).

titles(Books) ->
    [maps:get(<<"title">>, B) || B <- Books].
