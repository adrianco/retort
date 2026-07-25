-module(book_api_db).
-behaviour(gen_server).

-export([start_link/0, init/1, handle_call/3, handle_cast/2, handle_info/2, terminate/2, code_change/3]).
-export([init_db/0, get_all_books/0, get_book_by_id/1, create_book/1, update_book/2, delete_book/1]).

start_link() ->
    gen_server:start_link({local, ?MODULE}, ?MODULE, [], []).

init([]) ->
    {ok, init_db()}.

init_db() ->
    %% Create books table if not exists
    Sql = "CREATE TABLE IF NOT EXISTS books (" ++
            "id INTEGER PRIMARY KEY AUTOINCREMENT, " ++
            "title TEXT NOT NULL, " ++
            "author TEXT NOT NULL, " ++
            "year INTEGER, " ++
            "isbn TEXT)",
    case sqlite3:execute(":memory:", Sql) of
        {ok, _} -> ok;
        Error -> Error
    end.

get_all_books() ->
    case sqlite3:execute(":memory:", "SELECT * FROM books") of
        {ok, Rows} ->
            {ok, Rows};
        Error ->
            Error
    end.

get_book_by_id(Id) when is_integer(Id) ->
    Sql = "SELECT * FROM books WHERE id = ?",
    case sqlite3:execute(":memory:", {Sql, [Id]}) of
        {ok, [{Id2, Title, Author, Year, ISBN}]} ->
            {ok, #{id => Id2, title => Title, author => Author, year => Year, isbn => ISBN}};
        {ok, []} ->
            {error, not_found};
        Error ->
            Error
    end;
get_book_by_id(_Id) ->
    {error, invalid_id}.

create_book(#{title := Title, author := Author} = Book) ->
    Year = maps:get(year, Book, null),
    ISBN = maps:get(isbn, Book, null),
    Sql = "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
    case sqlite3:execute(":memory:", {Sql, [Title, Author, Year, ISBN]}) of
        {ok, _} ->
            %% Get the last inserted row
            case sqlite3:execute(":memory:", "SELECT * FROM books ORDER BY id DESC LIMIT 1") of
                {ok, [{Id, Title2, Author2, Year2, ISBN2}]} ->
                    {ok, #{id => Id, title => Title2, author => Author2, year => Year2, isbn => ISBN2}};
                Error ->
                    Error
            end;
        Error ->
            Error
    end;
create_book(_) ->
    {error, invalid_data}.

update_book(Id, Book) when is_integer(Id) ->
    case get_book_by_id(Id) of
        {ok, ExistingBook} ->
            NewBook = maps:merge(ExistingBook, Book),
            Sql = "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            case sqlite3:execute(":memory:", {Sql, [maps:get(title, NewBook), maps:get(author, NewBook), 
                                                    maps:get(year, NewBook, null), maps:get(isbn, NewBook, null), Id]}) of
                {ok, _} ->
                    {ok, NewBook};
                Error ->
                    Error
            end;
        {error, not_found} ->
            {error, not_found};
        Error ->
            Error
    end;
update_book(_Id, _Book) ->
    {error, invalid_id}.

delete_book(Id) when is_integer(Id) ->
    case get_book_by_id(Id) of
        {ok, _Book} ->
            Sql = "DELETE FROM books WHERE id = ?",
            case sqlite3:execute(":memory:", {Sql, [Id]}) of
                {ok, _} ->
                    {ok, deleted};
                Error ->
                    Error
            end;
        {error, not_found} ->
            {error, not_found};
        Error ->
            Error
    end;
delete_book(_Id) ->
    {error, invalid_id}.

handle_call(_Request, _From, State) ->
    {reply, ok, State}.

handle_cast(_Msg, State) ->
    {noreply, State}.

handle_info(_Info, State) ->
    {noreply, State}.

terminate(_Reason, _State) ->
    ok.

code_change(_OldVsn, State, _Extra) ->
    {ok, State}.
