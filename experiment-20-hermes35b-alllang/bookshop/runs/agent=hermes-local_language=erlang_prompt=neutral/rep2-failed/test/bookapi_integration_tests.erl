-module(bookapi_integration_tests).

-include_lib("eunit/include/eunit.hrl").

%% Integration tests for the HTTP API endpoints
%% Uses cowboy's test module to make HTTP requests against the running server

integration_test_() ->
    {setup,
        fun setup/0,
        fun teardown/1,
        [
            {"health_check_returns_200",
                fun health_check_test/0},
            {"health_check_returns_json",
                fun health_check_json_test/0},
            {"get_all_books_returns_200",
                fun get_all_books_test/0},
            {"get_books_with_author_filter",
                fun get_books_by_author_test/0},
            {"get_single_book_returns_200",
                fun get_single_book_test/0},
            {"get_nonexistent_book_returns_404",
                fun get_nonexistent_book_test/0},
            {"create_valid_book_returns_201",
                fun create_book_test/0},
            {"create_book_missing_title_returns_400",
                fun create_book_no_title_test/0},
            {"create_book_missing_author_returns_400",
                fun create_book_no_author_test/0},
            {"update_existing_book_returns_200",
                fun update_book_test/0},
            {"update_nonexistent_book_returns_404",
                fun update_nonexistent_book_test/0},
            {"delete_existing_book_returns_200",
                fun delete_book_test/0},
            {"delete_nonexistent_book_returns_404",
                fun delete_nonexistent_book_test/0}
        ]
    }.

setup() ->
    Port = 18921,
    ok = application:start(bookapi),
    delay(500),
    Port.

teardown(_Port) ->
    application:stop(bookapi),
    delay(500),
    ok.

delay(Ms) ->
    timer:sleep(Ms).

make_request(Path, Body) ->
    make_request(Path, [], Body).

make_request(Path, Headers, Body) ->
    case httpc:request(post,
        {"http://localhost:18921" ++ Path, Headers,
         [{"content-type", "application/json"}],
         Body},
        [], []) of
        {ok, {{_, Status, _}, _, RespBody}} ->
            {Status, jiffy:decode(RespBody, [return_maps])};
        {error, Reason} ->
            {error, Reason}
    end.

make_get_request(Path) ->
    case httpc:request(get, {"http://localhost:18921" ++ Path, []}, [], []) of
        {ok, {{_, Status, _}, _, RespBody}} ->
            {Status, jiffy:decode(RespBody, [return_maps])};
        {error, Reason} ->
            {error, Reason}
    end.

health_check_test() ->
    {Status, _} = make_get_request("/health"),
    ?assertEqual(200, Status).

health_check_json_test() ->
    {Status, Body} = make_get_request("/health"),
    ?assertEqual(200, Status),
    ?assertEqual(ok, Body#{status}).

get_all_books_test() ->
    {Status, Books} = make_get_request("/books"),
    ?assertEqual(200, Status),
    ?assert(is_list(Books)),
    ?assert(length(Books) >= 3),
    ?assertEqual(true, lists:any(fun(B) ->
        maps:get(title, B) =:= "The Great Gatsby"
    end, Books)).

get_books_by_author_test() ->
    {Status, Books} = make_get_request("/books?author=George%20Orwell"),
    ?assertEqual(200, Status),
    ?assert(is_list(Books)),
    ?assertEqual(1, length(Books)),
    ?assertEqual("1984", maps:get(title, lists:first(Books))).

get_single_book_test() ->
    {Status, Book} = make_get_request("/books/1"),
    ?assertEqual(200, Status),
    ?assertEqual("The Great Gatsby", maps:get(title, Book)),
    ?assertEqual("F. Scott Fitzgerald", maps:get(author, Book)).

get_nonexistent_book_test() ->
    {Status, _} = make_get_request("/books/9999"),
    ?assertEqual(404, Status).

create_book_test() ->
    Body = jiffy:encode(#{title => "Test Book", author => "Test Author",
                           year => 2024, isbn => "978-1111111111"}),
    {Status, Book} = make_request("/books", [], Body),
    ?assertEqual(201, Status),
    ?assertEqual("Test Book", maps:get(title, Book)),
    ?assertEqual("Test Author", maps:get(author, Book)).

create_book_no_title_test() ->
    Body = jiffy:encode(#{author => "Test Author", year => 2024, isbn => "isbn"}),
    {Status, _} = make_request("/books", [], Body),
    ?assertEqual(400, Status).

create_book_no_author_test() ->
    Body = jiffy:encode(#{title => "Test Book", year => 2024, isbn => "isbn"}),
    {Status, _} = make_request("/books", [], Body),
    ?assertEqual(400, Status).

update_book_test() ->
    Body = jiffy:encode(#{title => "Updated Title", author => "Updated Author"}),
    {Status, Book} = make_request("/books/1", [], Body),
    ?assertEqual(200, Status),
    ?assertEqual("Updated Title", maps:get(title, Book)),
    ?assertEqual("Updated Author", maps:get(author, Book)).

update_nonexistent_book_test() ->
    Body = jiffy:encode(#{title => "Ghost Book"}),
    {Status, _} = make_request("/books/9999", [], Body),
    ?assertEqual(404, Status).

delete_book_test() ->
    %% First ensure the book exists
    bookapi_db:create_book(#{title => "Delete Me", author => "Delete Author",
                             year => 2024, isbn => "999-999"}),
    delay(100),
    {Status, _} = make_request("/books/4", [], []),
    ?assertEqual(200, Status).

delete_nonexistent_book_test() ->
    {Status, _} = make_request("/books/99999", [], []),
    ?assertEqual(404, Status).
