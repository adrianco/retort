%%%-------------------------------------------------------------------
%%% @doc Unit tests for the pure validation/rendering logic in {@link book}.
%%% @end
%%%-------------------------------------------------------------------
-module(book_tests).

-include_lib("eunit/include/eunit.hrl").
-include("book_api.hrl").

%%%===================================================================
%%% Happy paths
%%%===================================================================

full_payload_test() ->
    Body = #{<<"title">> => <<"Dune">>,
             <<"author">> => <<"Frank Herbert">>,
             <<"year">> => 1965,
             <<"isbn">> => <<"978-0-441-01359-3">>},
    ?assertEqual({ok, #{title => <<"Dune">>,
                        author => <<"Frank Herbert">>,
                        year => 1965,
                        isbn => <<"978-0-441-01359-3">>}},
                 book:validate(Body)).

optional_fields_default_to_null_test() ->
    Body = #{<<"title">> => <<"Ulysses">>, <<"author">> => <<"James Joyce">>},
    ?assertEqual({ok, #{title => <<"Ulysses">>,
                        author => <<"James Joyce">>,
                        year => null,
                        isbn => null}},
                 book:validate(Body)).

explicit_nulls_are_accepted_test() ->
    Body = #{<<"title">> => <<"Ulysses">>, <<"author">> => <<"James Joyce">>,
             <<"year">> => null, <<"isbn">> => null},
    ?assertMatch({ok, #{year := null, isbn := null}}, book:validate(Body)).

surrounding_whitespace_is_trimmed_test() ->
    Body = #{<<"title">> => <<"  Emma  ">>, <<"author">> => <<"\tJane Austen\n">>},
    ?assertMatch({ok, #{title := <<"Emma">>, author := <<"Jane Austen">>}},
                 book:validate(Body)).

blank_isbn_becomes_null_test() ->
    ?assertMatch({ok, #{isbn := null}}, validate_with(#{<<"isbn">> => <<"   ">>})).

%%%===================================================================
%%% Required fields
%%%===================================================================

title_is_required_test() ->
    Body = #{<<"author">> => <<"Anon">>},
    ?assertEqual([{<<"title">>, <<"is required">>}],
                 errors(book:validate(Body))).

author_is_required_test() ->
    Body = #{<<"title">> => <<"Untitled">>},
    ?assertEqual([{<<"author">>, <<"is required">>}],
                 errors(book:validate(Body))).

blank_title_is_rejected_test() ->
    Body = #{<<"title">> => <<"   ">>, <<"author">> => <<"Anon">>},
    ?assertEqual([{<<"title">>, <<"must not be blank">>}],
                 errors(book:validate(Body))).

non_string_title_is_rejected_test() ->
    Body = #{<<"title">> => 42, <<"author">> => <<"Anon">>},
    ?assertEqual([{<<"title">>, <<"must be a string">>}],
                 errors(book:validate(Body))).

overlong_title_is_rejected_test() ->
    Body = #{<<"title">> => binary:copy(<<"x">>, 513), <<"author">> => <<"Anon">>},
    ?assertEqual([{<<"title">>, <<"must be at most 512 bytes">>}],
                 errors(book:validate(Body))).

%% All offending fields are reported at once, not just the first.
every_error_is_reported_test() ->
    Body = #{<<"year">> => <<"1965">>, <<"isbn">> => <<"nope">>},
    ?assertEqual([{<<"title">>, <<"is required">>},
                  {<<"author">>, <<"is required">>},
                  {<<"year">>, <<"must be an integer or null">>},
                  {<<"isbn">>, <<"must be a valid ISBN-10 or ISBN-13">>}],
                 errors(book:validate(Body))).

non_object_body_is_rejected_test() ->
    ?assertEqual([{<<"body">>, <<"must be a JSON object">>}],
                 errors(book:validate([1, 2, 3]))),
    ?assertEqual([{<<"body">>, <<"must be a JSON object">>}],
                 errors(book:validate(<<"a string">>))).

%%%===================================================================
%%% Optional fields
%%%===================================================================

year_must_be_an_integer_test() ->
    ?assertEqual([{<<"year">>, <<"must be an integer or null">>}],
                 errors(validate_with(#{<<"year">> => <<"1965">>}))),
    ?assertEqual([{<<"year">>, <<"must be an integer or null">>}],
                 errors(validate_with(#{<<"year">> => 1965.5}))).

year_must_be_in_range_test() ->
    ?assertEqual([{<<"year">>, <<"must be between -3000 and 2999">>}],
                 errors(validate_with(#{<<"year">> => 30000}))),
    ?assertMatch({ok, #{year := -800}}, validate_with(#{<<"year">> => -800})).

isbn_accepts_both_formats_test() ->
    ?assertMatch({ok, #{isbn := <<"0-306-40615-2">>}},
                 validate_with(#{<<"isbn">> => <<"0-306-40615-2">>})),
    ?assertMatch({ok, #{isbn := <<"9780306406157">>}},
                 validate_with(#{<<"isbn">> => <<"9780306406157">>})),
    %% ISBN-10 may end in a literal X check character.
    ?assertMatch({ok, #{isbn := <<"156619909X">>}},
                 validate_with(#{<<"isbn">> => <<"156619909X">>})).

isbn_rejects_wrong_length_or_alphabet_test() ->
    Invalid = [<<"123">>, <<"12345678901">>, <<"abcdefghij">>, <<"97803064061X7">>],
    [?assertEqual([{<<"isbn">>, <<"must be a valid ISBN-10 or ISBN-13">>}],
                  errors(validate_with(#{<<"isbn">> => I})))
     || I <- Invalid].

isbn_must_be_a_string_test() ->
    ?assertEqual([{<<"isbn">>, <<"must be a string or null">>}],
                 errors(validate_with(#{<<"isbn">> => 9780306406157}))).

%%%===================================================================
%%% Rendering
%%%===================================================================

to_map_renders_rfc3339_timestamps_test() ->
    Book = #book{id = 7, title = <<"Dune">>, author = <<"Frank Herbert">>,
                 year = 1965, isbn = null,
                 created_at = 0, updated_at = 1700000000},
    ?assertEqual(#{<<"id">> => 7,
                   <<"title">> => <<"Dune">>,
                   <<"author">> => <<"Frank Herbert">>,
                   <<"year">> => 1965,
                   <<"isbn">> => null,
                   <<"created_at">> => <<"1970-01-01T00:00:00Z">>,
                   <<"updated_at">> => <<"2023-11-14T22:13:20Z">>},
                 book:to_map(Book)).

to_map_survives_json_encoding_test() ->
    Title = <<"Ünïcøde \"quoted\" \\ backslash"/utf8>>,
    Book = #book{id = 1, title = Title, author = <<"A">>,
                 year = null, isbn = null, created_at = 0, updated_at = 0},
    Round = json:decode(iolist_to_binary(json:encode(book:to_map(Book)))),
    ?assertEqual(Title, maps:get(<<"title">>, Round)),
    ?assertEqual(null, maps:get(<<"year">>, Round)).

matches_author_ignores_case_test() ->
    Book = #book{author = <<"Ursula K. Le Guin">>},
    ?assert(book:matches_author(<<"ursula k. le guin">>, Book)),
    ?assert(book:matches_author(<<"URSULA K. LE GUIN">>, Book)),
    ?assertNot(book:matches_author(<<"Ursula">>, Book)).

%%%===================================================================
%%% Helpers
%%%===================================================================

%% Validate a minimal valid payload merged with `Extra'.
validate_with(Extra) ->
    Base = #{<<"title">> => <<"T">>, <<"author">> => <<"A">>},
    book:validate(maps:merge(Base, Extra)).

%% Flatten a validation result into {Field, Message} pairs for assertions.
errors({error, Errors}) ->
    [{maps:get(<<"field">>, E), maps:get(<<"message">>, E)} || E <- Errors];
errors(Other) ->
    erlang:error({expected_validation_error, Other}).
