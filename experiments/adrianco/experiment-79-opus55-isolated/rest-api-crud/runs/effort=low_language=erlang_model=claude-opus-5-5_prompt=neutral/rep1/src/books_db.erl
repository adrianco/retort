%% SQLite-backed storage for books. A single gen_server owns the connection.
-module(books_db).
-behaviour(gen_server).

-export([start_link/1, create/1, list/0, list/1, get/1, update/2, delete/1, delete_all/0]).
-export([init/1, handle_call/3, handle_cast/2, handle_info/2, terminate/2]).

-define(COLUMNS, "id, title, author, year, isbn").

start_link(Path) ->
    gen_server:start_link({local, ?MODULE}, ?MODULE, Path, []).

-spec create(map()) -> {ok, map()}.
create(Book) -> gen_server:call(?MODULE, {create, Book}).

-spec list() -> [map()].
list() -> list(undefined).

-spec list(undefined | binary()) -> [map()].
list(Author) -> gen_server:call(?MODULE, {list, Author}).

-spec get(integer()) -> {ok, map()} | not_found.
get(Id) -> gen_server:call(?MODULE, {get, Id}).

-spec update(integer(), map()) -> {ok, map()} | not_found.
update(Id, Book) -> gen_server:call(?MODULE, {update, Id, Book}).

-spec delete(integer()) -> ok | not_found.
delete(Id) -> gen_server:call(?MODULE, {delete, Id}).

delete_all() -> gen_server:call(?MODULE, delete_all).

%% gen_server

init(Path) ->
    {ok, Db} = esqlite3:open(Path),
    ok = esqlite3:exec(Db,
        "CREATE TABLE IF NOT EXISTS books ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "title TEXT NOT NULL, "
        "author TEXT NOT NULL, "
        "year INTEGER, "
        "isbn TEXT)"),
    {ok, Db}.

handle_call({create, Book}, _From, Db) ->
    [] = esqlite3:q(Db, "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
                    fields(Book)),
    Id = esqlite3:last_insert_rowid(Db),
    {reply, fetch(Db, Id), Db};
handle_call({list, undefined}, _From, Db) ->
    Rows = esqlite3:q(Db, "SELECT " ?COLUMNS " FROM books ORDER BY id"),
    {reply, [to_map(R) || R <- Rows], Db};
handle_call({list, Author}, _From, Db) ->
    Rows = esqlite3:q(Db, "SELECT " ?COLUMNS " FROM books WHERE author = ?1 ORDER BY id",
                      [Author]),
    {reply, [to_map(R) || R <- Rows], Db};
handle_call({get, Id}, _From, Db) ->
    {reply, fetch(Db, Id), Db};
handle_call({update, Id, Book}, _From, Db) ->
    [] = esqlite3:q(Db, "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 "
                        "WHERE id = ?5", fields(Book) ++ [Id]),
    {reply, fetch(Db, Id), Db};
handle_call({delete, Id}, _From, Db) ->
    [] = esqlite3:q(Db, "DELETE FROM books WHERE id = ?1", [Id]),
    Reply = case esqlite3:changes(Db) of
                0 -> not_found;
                _ -> ok
            end,
    {reply, Reply, Db};
handle_call(delete_all, _From, Db) ->
    ok = esqlite3:exec(Db, "DELETE FROM books"),
    {reply, ok, Db}.

handle_cast(_Msg, Db) -> {noreply, Db}.

handle_info(_Info, Db) -> {noreply, Db}.

terminate(_Reason, Db) ->
    esqlite3:close(Db),
    ok.

%% internal

fields(Book) ->
    [maps:get(title, Book), maps:get(author, Book),
     null_to_undefined(maps:get(year, Book)), null_to_undefined(maps:get(isbn, Book))].

null_to_undefined(null) -> undefined;
null_to_undefined(V) -> V.

fetch(Db, Id) ->
    case esqlite3:q(Db, "SELECT " ?COLUMNS " FROM books WHERE id = ?1", [Id]) of
        [Row] -> {ok, to_map(Row)};
        [] -> not_found
    end.

to_map([Id, Title, Author, Year, Isbn]) ->
    #{id => Id, title => Title, author => Author,
      year => undefined_to_null(Year), isbn => undefined_to_null(Isbn)}.

undefined_to_null(undefined) -> null;
undefined_to_null(V) -> V.
