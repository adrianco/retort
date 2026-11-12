%% @doc SQLite-backed storage for books. A single process owns the
%% connection, which serialises all database access.
-module(bookstore_db).
-behaviour(gen_server).

-export([start_link/1, create/1, list/1, get/1, update/2, delete/1, clear/0]).
-export([init/1, handle_call/3, handle_cast/2, terminate/2]).

-define(COLS, "id, title, author, year, isbn").

%%% API

start_link(Path) ->
    gen_server:start_link({local, ?MODULE}, ?MODULE, Path, []).

-spec create(map()) -> {ok, map()}.
create(Book) -> gen_server:call(?MODULE, {create, Book}).

%% Author is a binary to filter on, or undefined for all books.
-spec list(binary() | undefined) -> {ok, [map()]}.
list(Author) -> gen_server:call(?MODULE, {list, Author}).

-spec get(integer()) -> {ok, map()} | not_found.
get(Id) -> gen_server:call(?MODULE, {get, Id}).

-spec update(integer(), map()) -> {ok, map()} | not_found.
update(Id, Book) -> gen_server:call(?MODULE, {update, Id, Book}).

-spec delete(integer()) -> ok | not_found.
delete(Id) -> gen_server:call(?MODULE, {delete, Id}).

-spec clear() -> ok.
clear() -> gen_server:call(?MODULE, clear).

%%% gen_server

init(Path) ->
    {ok, Conn} = esqlite3:open(Path),
    ok = esqlite3:exec(Conn,
        "CREATE TABLE IF NOT EXISTS books ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "title TEXT NOT NULL, "
        "author TEXT NOT NULL, "
        "year INTEGER, "
        "isbn TEXT)"),
    {ok, Conn}.

handle_call({create, #{title := T, author := A, year := Y, isbn := I}}, _From, Conn) ->
    [] = esqlite3:q(Conn,
        "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
        [T, A, to_sql(Y), to_sql(I)]),
    Id = esqlite3:last_insert_rowid(Conn),
    {reply, fetch(Conn, Id), Conn};
handle_call({list, undefined}, _From, Conn) ->
    Rows = esqlite3:q(Conn, "SELECT " ?COLS " FROM books ORDER BY id"),
    {reply, {ok, [to_book(R) || R <- Rows]}, Conn};
handle_call({list, Author}, _From, Conn) ->
    Rows = esqlite3:q(Conn,
        "SELECT " ?COLS " FROM books WHERE author = ?1 ORDER BY id", [Author]),
    {reply, {ok, [to_book(R) || R <- Rows]}, Conn};
handle_call({get, Id}, _From, Conn) ->
    {reply, fetch(Conn, Id), Conn};
handle_call({update, Id, #{title := T, author := A, year := Y, isbn := I}}, _From, Conn) ->
    [] = esqlite3:q(Conn,
        "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
        [T, A, to_sql(Y), to_sql(I), Id]),
    {reply, fetch(Conn, Id), Conn};
handle_call({delete, Id}, _From, Conn) ->
    [] = esqlite3:q(Conn, "DELETE FROM books WHERE id = ?1", [Id]),
    Reply = case esqlite3:changes(Conn) of
        0 -> not_found;
        _ -> ok
    end,
    {reply, Reply, Conn};
handle_call(clear, _From, Conn) ->
    ok = esqlite3:exec(Conn, "DELETE FROM books"),
    {reply, ok, Conn}.

handle_cast(_Msg, Conn) ->
    {noreply, Conn}.

terminate(_Reason, Conn) ->
    esqlite3:close(Conn).

%%% internal

fetch(Conn, Id) ->
    case esqlite3:q(Conn, "SELECT " ?COLS " FROM books WHERE id = ?1", [Id]) of
        [Row] -> {ok, to_book(Row)};
        [] -> not_found
    end.

to_book([Id, Title, Author, Year, Isbn]) ->
    #{id => Id, title => Title, author => Author,
      year => from_sql(Year), isbn => from_sql(Isbn)}.

to_sql(null) -> undefined;
to_sql(V) -> V.

from_sql(undefined) -> null;
from_sql(V) -> V.
