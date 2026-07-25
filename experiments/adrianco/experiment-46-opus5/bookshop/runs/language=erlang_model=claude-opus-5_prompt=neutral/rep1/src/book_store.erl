%%%-------------------------------------------------------------------
%%% @doc Persistence layer for books, backed by Mnesia's `disc_copies'
%%% storage — the embedded, transactional database that ships with OTP.
%%%
%%% Two tables are used:
%%% <ul>
%%%   <li>`book' — an `ordered_set' keyed by the auto-incrementing id, so
%%%       listing yields books in insertion order without a sort.</li>
%%%   <li>`book_counter' — holds the id sequence, bumped atomically by
%%%       `mnesia:dirty_update_counter/3'.</li>
%%% </ul>
%%% @end
%%%-------------------------------------------------------------------
-module(book_store).

-include("book_api.hrl").

-export([init/1, stop/0]).
-export([create/1, list/0, list_by_author/1, get/1, update/2, delete/1, count/0]).

%% Only ever touched through mnesia:dirty_update_counter/3, so the compiler
%% sees no literal use beyond record_info/2 below.
-compile({nowarn_unused_record, [book_counter]}).
-record(book_counter, {name :: atom(), value :: integer()}).

-define(TABLES, [book, book_counter]).
-define(WAIT_TIMEOUT, 30000).

%%%===================================================================
%%% Lifecycle
%%%===================================================================

%% @doc Point Mnesia at `Dir', create the schema and tables if they are
%% missing, and wait until they are loaded. Safe to call repeatedly.
-spec init(file:filename_all()) -> ok.
init(Dir) ->
    _ = mnesia:stop(),
    ok = filelib:ensure_path(Dir),
    ok = application:set_env(mnesia, dir, Dir),
    ok = ensure_schema(),
    ok = mnesia:start(),
    ok = ensure_table(book,
                      [{type, ordered_set},
                       {attributes, record_info(fields, book)},
                       {disc_copies, [node()]}]),
    ok = ensure_table(book_counter,
                      [{attributes, record_info(fields, book_counter)},
                       {disc_copies, [node()]}]),
    ok = mnesia:wait_for_tables(?TABLES, ?WAIT_TIMEOUT).

-spec stop() -> ok.
stop() ->
    _ = mnesia:stop(),
    ok.

ensure_schema() ->
    case mnesia:create_schema([node()]) of
        ok -> ok;
        {error, {_Node, {already_exists, _}}} -> ok;
        {error, Reason} -> erlang:error({mnesia_schema_failed, Reason})
    end.

ensure_table(Name, Opts) ->
    case mnesia:create_table(Name, Opts) of
        {atomic, ok} -> ok;
        {aborted, {already_exists, Name}} -> ok;
        {aborted, Reason} -> erlang:error({mnesia_table_failed, Name, Reason})
    end.

%%%===================================================================
%%% CRUD
%%%===================================================================

%% @doc Insert a new book and return it with its freshly allocated id.
-spec create(book:attrs()) -> {ok, #book{}}.
create(#{title := Title, author := Author, year := Year, isbn := Isbn}) ->
    Now = erlang:system_time(second),
    Id = mnesia:dirty_update_counter(book_counter, book_id, 1),
    Book = #book{id = Id, title = Title, author = Author, year = Year,
                 isbn = Isbn, created_at = Now, updated_at = Now},
    {atomic, ok} = mnesia:transaction(fun() -> mnesia:write(Book) end),
    {ok, Book}.

%% @doc All books, ordered by id ascending.
-spec list() -> [#book{}].
list() ->
    {atomic, Books} =
        mnesia:transaction(
          fun() ->
              mnesia:foldr(fun(Book, Acc) -> [Book | Acc] end, [], book)
          end),
    Books.

%% @doc Books whose author matches `Author', compared case-insensitively.
-spec list_by_author(binary()) -> [#book{}].
list_by_author(Author) ->
    [B || B <- list(), book:matches_author(Author, B)].

-spec get(pos_integer()) -> {ok, #book{}} | {error, not_found}.
get(Id) ->
    case mnesia:dirty_read(book, Id) of
        [Book] -> {ok, Book};
        [] -> {error, not_found}
    end.

%% @doc Replace the mutable fields of an existing book. The id and the
%% creation timestamp are preserved.
-spec update(pos_integer(), book:attrs()) -> {ok, #book{}} | {error, not_found}.
update(Id, #{title := Title, author := Author, year := Year, isbn := Isbn}) ->
    Fun = fun() ->
              case mnesia:read(book, Id, write) of
                  [] ->
                      {error, not_found};
                  [Existing] ->
                      Updated = Existing#book{title = Title,
                                              author = Author,
                                              year = Year,
                                              isbn = Isbn,
                                              updated_at = erlang:system_time(second)},
                      ok = mnesia:write(Updated),
                      {ok, Updated}
              end
          end,
    {atomic, Result} = mnesia:transaction(Fun),
    Result.

-spec delete(pos_integer()) -> ok | {error, not_found}.
delete(Id) ->
    Fun = fun() ->
              case mnesia:read(book, Id, write) of
                  [] -> {error, not_found};
                  [_] -> mnesia:delete({book, Id})
              end
          end,
    {atomic, Result} = mnesia:transaction(Fun),
    Result.

-spec count() -> non_neg_integer().
count() ->
    mnesia:table_info(book, size).
