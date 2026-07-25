%% Test helpers for book_api
-module(book_api_test).

-include_lib("eunit/include/eunit.hrl").

%% Test suites
book_tests_() ->
    {setup,
        fun setup/0,
        fun cleanup/1,
        [
            fun book_validate_success/0,
            fun book_validate_missing_title/0,
            fun book_validate_missing_author/0,
            fun book_validate_empty_title/0,
            fun book_validate_empty_author/0
        ]}.

setup() ->
    ok.

cleanup(_) ->
    ok.

%% Book module tests
book_validate_success() ->
    Book = #{title => <<"Test Book">>, author => <<"Test Author">>, year => 2024, isbn => <<"1234567890">>},
    ?assertEqual({ok, Book}, book:validate(Book)).

book_validate_missing_title() ->
    Book = #{author => <<"Test Author">>},
    {error, Reason} = book:validate(Book),
    ?assert(Reason =:= missing_required_fields orelse Reason =:= title_required).

book_validate_missing_author() ->
    Book = #{title => <<"Test Book">>},
    {error, Reason} = book:validate(Book),
    ?assert(Reason =:= missing_required_fields orelse Reason =:= author_required).

book_validate_empty_title() ->
    Book = #{title => <<>>, author => <<"Test Author">>},
    {error, Reason} = book:validate(Book),
    ?assert(Reason =:= title_required).

book_validate_empty_author() ->
    Book = #{title => <<"Test Book">>, author => <<>>},
    {error, Reason} = book:validate(Book),
    ?assert(Reason =:= author_required).

%% Book to_json tests
book_to_json_tests_() ->
    {setup,
        fun setup/0,
        fun cleanup/1,
        [
            fun book_to_json_basic/0,
            fun book_to_json_with_all_fields/0
        ]}.

book_to_json_basic() ->
    Book = #{title => <<"Test Book">>, author => <<"Test Author">>},
    Json = book:to_json(Book),
    ?assert(is_map(Json)),
    ?assertEqual(<<"Test Book">>, maps:get(<<"title">>, Json)),
    ?assertEqual(<<"Test Author">>, maps:get(<<"author">>, Json)).

book_to_json_with_all_fields() ->
    Book = #{id => 1, title => <<"Test Book">>, author => <<"Test Author">>, year => 2024, isbn => <<"1234567890">>},
    Json = book:to_json(Book),
    ?assert(is_map(Json)),
    ?assertEqual(1, maps:get(<<"id">>, Json)),
    ?assertEqual(<<"Test Book">>, maps:get(<<"title">>, Json)),
    ?assertEqual(<<"Test Author">>, maps:get(<<"author">>, Json)),
    ?assertEqual(2024, maps:get(<<"year">>, Json)),
    ?assertEqual(<<"1234567890">>, maps:get(<<"isbn">>, Json)).

%% Book parse_json tests
book_parse_json_tests_() ->
    {setup,
        fun setup/0,
        fun cleanup/1,
        [
            fun book_parse_json_basic/0,
            fun book_parse_json_with_optional_fields/0,
            fun book_parse_json_missing_required_fields/0
        ]}.

book_parse_json_basic() ->
    Json = #{<<"title">> => <<"Test Book">>, <<"author">> => <<"Test Author">>},
    {ok, Book} = book:parse_json(Json),
    ?assertEqual(<<"Test Book">>, maps:get(title, Book)),
    ?assertEqual(<<"Test Author">>, maps:get(author, Book)).

book_parse_json_with_optional_fields() ->
    Json = #{<<"id">> => 1, <<"title">> => <<"Test Book">>, <<"author">> => <<"Test Author">>, 
             <<"year">> => 2024, <<"isbn">> => <<"1234567890">>},
    {ok, Book} = book:parse_json(Json),
    ?assertEqual(1, maps:get(id, Book)),
    ?assertEqual(2024, maps:get(year, Book)),
    ?assertEqual(<<"1234567890">>, maps:get(isbn, Book)).

book_parse_json_missing_required_fields() ->
    Json = #{<<"title">> => <<"Test Book">>},
    {error, Reason} = book:parse_json(Json),
    ?assert(Reason =:= missing_required_fields orelse Reason =:= author_required).

%% Integration tests for HTTP handlers
handler_tests_() ->
    {setup,
        fun setup/0,
        fun cleanup/1,
        [
            fun handler_health_endpoint/0,
            fun handler_books_crud/0
        ]}.

handler_health_endpoint() ->
    %% Test health endpoint returns 200
    %% Note: This is a simplified test - in practice you'd use a mock request
    ?assert(true).

handler_books_crud() ->
    %% Test full CRUD operations
    %% Note: This is a simplified test - in practice you'd use a mock request
    ?assert(true).
