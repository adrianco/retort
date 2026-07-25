%% -*- erlang -*-
%% This file is part of Book API.
%%
%% Book API is free software: you can redistribute it and/or modify
%% it under the terms of the GNU Lesser General Public License as published by
%% the Free Software Foundation, either version 3 of the License, or
%% (at your option) any later version.
%%
%% Book API is distributed in the hope that it will be useful,
%% but WITHOUT ANY WARRANTY; without even the implied warranty of
%% MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
%% GNU Lesser General Public License for more details.
%%
%% You should have received a copy of the GNU Lesser General Public License
%% along with Book API. If not, see <http://www.gnu.org/licenses/>.

-module(book_api_db).

-behaviour(gen_server).

-export([start_link/0, init/1, handle_call/3, handle_cast/2, handle_info/2, terminate/2, code_change/3]).

-export([
    % CRUD operations
    create_book/1,
    get_book/1,
    get_books/1,
    update_book/2,
    delete_book/1,
    
    % Health check
    health_check/0,
    
    % DB path
    get_db_path/0
]).

-record(book, {id, title, author, year, isbn}).

get_db_path() ->
    case application:get_env(book_api, db_path) of
        {ok, Path} -> Path;
        undefined -> "books.db"
    end.

start_link() ->
    gen_server:start_link({local, ?MODULE}, ?MODULE, [], []).

init([]) ->
    ok = init_db(),
    {ok, #{}}.

init_db() ->
    DbPath = get_db_path(),
    {ok, Conn} = esqlite:open(DbPath),
    Query = "CREATE TABLE IF NOT EXISTS books ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "title TEXT NOT NULL, "
            "author TEXT NOT NULL, "
            "year INTEGER, "
            "isbn TEXT UNIQUE"
            ");",
    {ok, _} = esqlite:query(Conn, Query),
    esqlite:close(Conn),
    ok.

%% API functions

create_book(#{title := Title, author := Author} = Data) ->
    Year = maps:get(year, Data, null),
    Isbn = maps:get(isbn, Data, null),
    gen_server:call(?MODULE, {create_book, Title, Author, Year, Isbn}).

get_book(Id) when is_integer(Id) orelse is_binary(Id) orelse is_atom(Id) ->
    gen_server:call(?MODULE, {get_book, Id}).

get_books(#{author := Author} = _Params) ->
    gen_server:call(?MODULE, {get_books_by_author, Author});
get_books(_Params) ->
    gen_server:call(?MODULE, get_books).

update_book(Id, Data) when is_map(Data) ->
    gen_server:call(?MODULE, {update_book, Id, Data}).

delete_book(Id) when is_integer(Id) orelse is_binary(Id) orelse is_atom(Id) ->
    gen_server:call(?MODULE, {delete_book, Id}).

health_check() ->
    DbPath = get_db_path(),
    {ok, Conn} = esqlite:open(DbPath),
    {ok, _} = esqlite:query(Conn, "SELECT 1"),
    esqlite:close(Conn),
    ok.

%% gen_server callbacks

handle_call({create_book, Title, Author, Year, Isbn}, _From, State) ->
    DbPath = get_db_path(),
    {ok, Conn} = esqlite:open(DbPath),
    Query = "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?);",
    Params = [Title, Author, Year, Isbn],
    try
        {ok, _} = esqlite:query(Conn, Query, Params),
        Id = esqlite:last_insert_rowid(Conn),
        esqlite:close(Conn),
        {reply, {ok, #{id => Id, title => Title, author => Author, year => Year, isbn => Isbn}}, State}
    catch
        _:_ -> esqlite:close(Conn), {reply, {error, duplicate_isbn}, State}
    end;

handle_call({get_book, Id}, _From, State) ->
    DbPath = get_db_path(),
    {ok, Conn} = esqlite:open(DbPath),
    Query = "SELECT id, title, author, year, isbn FROM books WHERE id = ?;",
    Params = [Id],
    case esqlite:query(Conn, Query, Params) of
        {ok, Rows} ->
            esqlite:close(Conn),
            case Rows of
                [] -> {reply, {error, not_found}, State};
                [[Id1, Title, Author, Year, Isbn]] ->
                    {reply, {ok, #book{id=Id1, title=Title, author=Author, year=Year, isbn=Isbn}}, State}
            end;
        _ ->
            esqlite:close(Conn),
            {reply, {error, db_error}, State}
    end;

handle_call(get_books, _From, State) ->
    DbPath = get_db_path(),
    {ok, Conn} = esqlite:open(DbPath),
    Query = "SELECT id, title, author, year, isbn FROM books;",
    case esqlite:query(Conn, Query) of
        {ok, Rows} ->
            esqlite:close(Conn),
            Books = lists:map(fun([Id, Title, Author, Year, Isbn]) ->
                #book{id=Id, title=Title, author=Author, year=Year, isbn=Isbn}
            end, Rows),
            {reply, {ok, Books}, State};
        _ ->
            esqlite:close(Conn),
            {reply, {error, db_error}, State}
    end;

handle_call({get_books_by_author, Author}, _From, State) ->
    DbPath = get_db_path(),
    {ok, Conn} = esqlite:open(DbPath),
    Query = "SELECT id, title, author, year, isbn FROM books WHERE author = ?;",
    case esqlite:query(Conn, Query, [Author]) of
        {ok, Rows} ->
            esqlite:close(Conn),
            Books = lists:map(fun([Id, Title, Author1, Year, Isbn]) ->
                #book{id=Id, title=Title, author=Author1, year=Year, isbn=Isbn}
            end, Rows),
            {reply, {ok, Books}, State};
        _ ->
            esqlite:close(Conn),
            {reply, {error, db_error}, State}
    end;

handle_call({update_book, Id, Data}, _From, State) ->
    DbPath = get_db_path(),
    {ok, Conn} = esqlite:open(DbPath),
    Title = maps:get(title, Data, undefined),
    Author = maps:get(author, Data, undefined),
    Year = maps:get(year, Data, undefined),
    Isbn = maps:get(isbn, Data, undefined),
    
    % Build update query dynamically
    UpdateFields = lists:filtermap(
        fun({title, Val}) when Val =/= undefined -> {true, {title, Val}};
           ({author, Val}) when Val =/= undefined -> {true, {author, Val}};
           ({year, Val}) when Val =/= undefined -> {true, {year, Val}};
           ({isbn, Val}) when Val =/= undefined -> {true, {isbn, Val}};
           (_) -> false
        end, maps:to_list(Data)),
    
    case UpdateFields of
        [] ->
            esqlite:close(Conn),
            {reply, {error, no_fields_to_update}, State};
        _ ->
            SetClause = string:join(
                [io_lib:format("~s = ?", [K]) || {K, _} <- UpdateFields], ", "),
            Params = [V || {_, V} <- UpdateFields] ++ [Id],
            Query = io_lib:format("UPDATE books SET ~s WHERE id = ?;", [SetClause]),
            case esqlite:query(Conn, lists:flatten(Query), Params) of
                {ok, _} ->
                    case get_book(Id) of
                        {ok, Book} ->
                            esqlite:close(Conn),
                            {reply, {ok, Book}, State};
                        {error, not_found} ->
                            esqlite:close(Conn),
                            {reply, {error, not_found}, State}
                    end;
                _ ->
                    esqlite:close(Conn),
                    {reply, {error, db_error}, State}
            end
    end;

handle_call({delete_book, Id}, _From, State) ->
    DbPath = get_db_path(),
    {ok, Conn} = esqlite:open(DbPath),
    Query = "DELETE FROM books WHERE id = ?;",
    case esqlite:query(Conn, Query, [Id]) of
        {ok, _} ->
            esqlite:close(Conn),
            {reply, ok, State};
        _ ->
            esqlite:close(Conn),
            {reply, {error, db_error}, State}
    end;

handle_call(_Request, _From, State) ->
    {reply, {error, unknown_request}, State}.

handle_cast(_Msg, State) ->
    {noreply, State}.

handle_info(_Info, State) ->
    {noreply, State}.

terminate(_Reason, _State) ->
    ok.

code_change(_OldVsn, State, _Extra) ->
    {ok, State}.
