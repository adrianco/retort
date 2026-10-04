%% Owns the SQLite connection and serialises all access to it.
-module(books_db).
-behaviour(gen_server).

-export([start_link/0, create/1, list/1, get/1, update/2, delete/1, delete_all/0]).
-export([init/1, handle_call/3, handle_cast/2, handle_info/2, terminate/2]).

-define(COLUMNS, "id, title, author, year, isbn").

start_link() ->
    gen_server:start_link({local, ?MODULE}, ?MODULE, [], []).

-spec create(map()) -> {ok, map()}.
create(Book) ->
    gen_server:call(?MODULE, {create, Book}).

%% Author is `undefined` for no filter.
-spec list(binary() | undefined) -> {ok, [map()]}.
list(Author) ->
    gen_server:call(?MODULE, {list, Author}).

-spec get(integer()) -> {ok, map()} | not_found.
get(Id) ->
    gen_server:call(?MODULE, {get, Id}).

-spec update(integer(), map()) -> {ok, map()} | not_found.
update(Id, Book) ->
    gen_server:call(?MODULE, {update, Id, Book}).

-spec delete(integer()) -> ok | not_found.
delete(Id) ->
    gen_server:call(?MODULE, {delete, Id}).

-spec delete_all() -> ok.
delete_all() ->
    gen_server:call(?MODULE, delete_all).

init([]) ->
    Path = application:get_env(books, db_path, "books.db"),
    {ok, Db} = esqlite3:open(Path),
    ok = esqlite3:exec(
        Db,
        "CREATE TABLE IF NOT EXISTS books ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "title TEXT NOT NULL, "
        "author TEXT NOT NULL, "
        "year INTEGER, "
        "isbn TEXT)"
    ),
    {ok, Db}.

handle_call({create, Book}, _From, Db) ->
    [] = esqlite3:q(
        Db,
        "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
        params(Book)
    ),
    Id = esqlite3:last_insert_rowid(Db),
    {reply, fetch(Db, Id), Db};
handle_call({list, undefined}, _From, Db) ->
    Rows = esqlite3:q(Db, "SELECT " ?COLUMNS " FROM books ORDER BY id"),
    {reply, {ok, [to_map(R) || R <- Rows]}, Db};
handle_call({list, Author}, _From, Db) ->
    Rows = esqlite3:q(
        Db,
        "SELECT " ?COLUMNS " FROM books WHERE author = ?1 ORDER BY id",
        [Author]
    ),
    {reply, {ok, [to_map(R) || R <- Rows]}, Db};
handle_call({get, Id}, _From, Db) ->
    {reply, fetch(Db, Id), Db};
handle_call({update, Id, Book}, _From, Db) ->
    [] = esqlite3:q(
        Db,
        "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
        params(Book) ++ [Id]
    ),
    {reply, fetch(Db, Id), Db};
handle_call({delete, Id}, _From, Db) ->
    [] = esqlite3:q(Db, "DELETE FROM books WHERE id = ?1", [Id]),
    Reply =
        case esqlite3:changes(Db) of
            0 -> not_found;
            _ -> ok
        end,
    {reply, Reply, Db};
handle_call(delete_all, _From, Db) ->
    ok = esqlite3:exec(Db, "DELETE FROM books"),
    {reply, ok, Db}.

handle_cast(_Msg, Db) ->
    {noreply, Db}.

handle_info(_Info, Db) ->
    {noreply, Db}.

terminate(_Reason, Db) ->
    esqlite3:close(Db).

fetch(Db, Id) ->
    case esqlite3:q(Db, "SELECT " ?COLUMNS " FROM books WHERE id = ?1", [Id]) of
        [Row] -> {ok, to_map(Row)};
        [] -> not_found
    end.

params(#{title := Title, author := Author, year := Year, isbn := Isbn}) ->
    [Title, Author, to_sql(Year), to_sql(Isbn)].

to_sql(null) -> undefined;
to_sql(V) -> V.

from_sql(undefined) -> null;
from_sql(V) -> V.

to_map([Id, Title, Author, Year, Isbn]) ->
    #{
        id => Id,
        title => Title,
        author => Author,
        year => from_sql(Year),
        isbn => from_sql(Isbn)
    }.
