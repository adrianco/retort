%%% @doc Mnesia-backed storage for the book collection.
-module(book_store).

-include("book_records.hrl").

-export([
    init/0,
    create/1,
    list/0,
    list_by_author/1,
    get/1,
    update/2,
    delete/1,
    to_map/1
]).

%% @doc Create the Mnesia schema and tables. Idempotent.
-spec init() -> ok.
init() ->
    mnesia:create_table(book, [
        {attributes, record_info(fields, book)},
        {ram_copies, [node()]}
    ]),
    mnesia:create_table(counter, [
        {attributes, record_info(fields, counter)},
        {ram_copies, [node()]}
    ]),
    ok = mnesia:wait_for_tables([book, counter], 5000),
    ok.

%% @doc Insert a new book. `Fields' is a map with binary values for
%% title/author and optional year/isbn. Returns the stored book as a map.
-spec create(map()) -> {ok, map()}.
create(Fields) ->
    Id = next_id(),
    Book = #book{
        id = Id,
        title = maps:get(title, Fields),
        author = maps:get(author, Fields),
        year = maps:get(year, Fields, undefined),
        isbn = maps:get(isbn, Fields, undefined)
    },
    {atomic, ok} = mnesia:transaction(fun() -> mnesia:write(Book) end),
    {ok, to_map(Book)}.

%% @doc List all books.
-spec list() -> [map()].
list() ->
    {atomic, Books} = mnesia:transaction(fun() ->
        mnesia:match_object(#book{_ = '_'})
    end),
    sort_and_map(Books).

%% @doc List books written by a given author (exact match).
-spec list_by_author(binary()) -> [map()].
list_by_author(Author) ->
    {atomic, Books} = mnesia:transaction(fun() ->
        mnesia:match_object(#book{author = Author, _ = '_'})
    end),
    sort_and_map(Books).

%% @doc Fetch a single book by id.
-spec get(integer()) -> {ok, map()} | {error, not_found}.
get(Id) ->
    {atomic, Result} = mnesia:transaction(fun() -> mnesia:read(book, Id) end),
    case Result of
        [Book] -> {ok, to_map(Book)};
        [] -> {error, not_found}
    end.

%% @doc Update an existing book, merging `Fields' over the stored values.
-spec update(integer(), map()) -> {ok, map()} | {error, not_found}.
update(Id, Fields) ->
    Fun = fun() ->
        case mnesia:read(book, Id) of
            [Book] ->
                Updated = Book#book{
                    title = maps:get(title, Fields, Book#book.title),
                    author = maps:get(author, Fields, Book#book.author),
                    year = maps:get(year, Fields, Book#book.year),
                    isbn = maps:get(isbn, Fields, Book#book.isbn)
                },
                mnesia:write(Updated),
                {ok, Updated};
            [] ->
                {error, not_found}
        end
    end,
    case mnesia:transaction(Fun) of
        {atomic, {ok, Book}} -> {ok, to_map(Book)};
        {atomic, {error, not_found}} -> {error, not_found}
    end.

%% @doc Delete a book by id.
-spec delete(integer()) -> ok | {error, not_found}.
delete(Id) ->
    Fun = fun() ->
        case mnesia:read(book, Id) of
            [_] -> mnesia:delete({book, Id});
            [] -> {error, not_found}
        end
    end,
    case mnesia:transaction(Fun) of
        {atomic, ok} -> ok;
        {atomic, {error, not_found}} -> {error, not_found}
    end.

%% @doc Convert a book record into a JSON-friendly map.
-spec to_map(#book{}) -> map().
to_map(#book{id = Id, title = Title, author = Author, year = Year, isbn = Isbn}) ->
    #{
        <<"id">> => Id,
        <<"title">> => Title,
        <<"author">> => Author,
        <<"year">> => null_if_undefined(Year),
        <<"isbn">> => null_if_undefined(Isbn)
    }.

%%% Internal helpers

next_id() ->
    mnesia:dirty_update_counter(counter, book_id, 1).

sort_and_map(Books) ->
    Sorted = lists:sort(fun(A, B) -> A#book.id =< B#book.id end, Books),
    [to_map(B) || B <- Sorted].

null_if_undefined(undefined) -> null;
null_if_undefined(Value) -> Value.
