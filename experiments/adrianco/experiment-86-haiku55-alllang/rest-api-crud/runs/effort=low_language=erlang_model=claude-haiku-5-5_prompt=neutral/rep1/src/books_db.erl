%% Owns the SQLite connection. All access is serialised through this process.
-module(books_db).
-behaviour(gen_server).

-export([start_link/1, ping/0, insert/1, list/1, get/1, update/2, delete/1]).
-export([init/1, handle_call/3, handle_cast/2, terminate/2]).

-define(SCHEMA,
        "CREATE TABLE IF NOT EXISTS books ("
        "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "  title TEXT NOT NULL,"
        "  author TEXT NOT NULL,"
        "  year INTEGER,"
        "  isbn TEXT)").

-define(COLUMNS, "id, title, author, year, isbn").

-type book() :: #{id := pos_integer(),
                  title := binary(),
                  author := binary(),
                  year := non_neg_integer() | null,
                  isbn := binary() | null}.

-export_type([book/0]).

start_link(DbPath) ->
    gen_server:start_link({local, ?MODULE}, ?MODULE, DbPath, []).

-spec ping() -> ok | {error, term()}.
ping() -> gen_server:call(?MODULE, ping).

%% Attrs: #{title, author, year, isbn}; year and isbn may be null.
-spec insert(map()) -> book().
insert(Attrs) -> gen_server:call(?MODULE, {insert, Attrs}).

%% Author is an optional case-insensitive exact match; undefined lists all.
-spec list(binary() | undefined) -> [book()].
list(Author) -> gen_server:call(?MODULE, {list, Author}).

-spec get(pos_integer()) -> {ok, book()} | not_found.
get(Id) -> gen_server:call(?MODULE, {get, Id}).

-spec update(pos_integer(), map()) -> {ok, book()} | not_found.
update(Id, Attrs) -> gen_server:call(?MODULE, {update, Id, Attrs}).

-spec delete(pos_integer()) -> ok | not_found.
delete(Id) -> gen_server:call(?MODULE, {delete, Id}).

init(DbPath) ->
    {ok, Db} = esqlite3:open(DbPath),
    ok = esqlite3:exec(Db, ?SCHEMA),
    {ok, Db}.

handle_call(ping, _From, Db) ->
    Reply = try run("SELECT 1", [], Db) of
                [[1]] -> ok;
                Other -> {error, Other}
            catch
                error:Reason -> {error, Reason}
            end,
    {reply, Reply, Db};
handle_call({insert, #{title := Title, author := Author, year := Year, isbn := Isbn}}, _From, Db) ->
    run("INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
        [Title, Author, Year, Isbn], Db),
    Id = esqlite3:last_insert_rowid(Db),
    {reply, row_to_book([Id, Title, Author, Year, Isbn]), Db};
handle_call({list, undefined}, _From, Db) ->
    Rows = run("SELECT " ?COLUMNS " FROM books ORDER BY id", [], Db),
    {reply, [row_to_book(R) || R <- Rows], Db};
handle_call({list, Author}, _From, Db) ->
    Rows = run("SELECT " ?COLUMNS " FROM books WHERE author = ?1 COLLATE NOCASE ORDER BY id",
               [Author], Db),
    {reply, [row_to_book(R) || R <- Rows], Db};
handle_call({get, Id}, _From, Db) ->
    {reply, fetch(Id, Db), Db};
handle_call({update, Id, #{title := Title, author := Author, year := Year, isbn := Isbn}}, _From, Db) ->
    case fetch(Id, Db) of
        not_found ->
            {reply, not_found, Db};
        {ok, _} ->
            run("UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
                [Title, Author, Year, Isbn, Id], Db),
            {reply, fetch(Id, Db), Db}
    end;
handle_call({delete, Id}, _From, Db) ->
    case fetch(Id, Db) of
        not_found ->
            {reply, not_found, Db};
        {ok, _} ->
            run("DELETE FROM books WHERE id = ?1", [Id], Db),
            {reply, ok, Db}
    end.

handle_cast(_Msg, Db) ->
    {noreply, Db}.

terminate(_Reason, Db) ->
    esqlite3:close(Db),
    ok.

%% esqlite3 returns {error, _} rather than raising; turn that into a crash
%% so the supervisor restarts the process instead of corrupting state.
run(Sql, Args, Db) ->
    case esqlite3:q(Db, Sql, Args) of
        {error, Reason} -> erlang:error({sql_error, Reason});
        Rows -> Rows
    end.

fetch(Id, Db) ->
    case run("SELECT " ?COLUMNS " FROM books WHERE id = ?1", [Id], Db) of
        [Row] -> {ok, row_to_book(Row)};
        [] -> not_found
    end.

row_to_book([Id, Title, Author, Year, Isbn]) ->
    #{id => Id, title => Title, author => Author,
      year => nullable(Year), isbn => nullable(Isbn)}.

nullable(undefined) -> null;
nullable(Value) -> Value.
