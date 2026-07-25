-module(book_api_db).

-behaviour(gen_server).

-export([start_link/0]).
-export([
    init_book_db/0,
    get_all_books/0,
    get_book_by_id/1,
    create_book/1,
    update_book/2,
    delete_book/1,
    health_check/0
]).

-export([init/1, handle_call/3, handle_cast/2, handle_info/2, terminate/2, code_change/3]).

-record(state, {
    db_path :: atom()
}).

start_link() ->
    gen_server:start_link({local, ?MODULE}, ?MODULE, [], []).

init_book_db() ->
    DbPath = 'books.db',
    case filelib:is_file(DbPath) of
        true -> ok;
        false ->
            {ok, Pid} = sqlite3:open(DbPath),
            Sql = "CREATE TABLE IF NOT EXISTS books (" ++
                    "id INTEGER PRIMARY KEY AUTOINCREMENT, " ++
                    "title TEXT NOT NULL, " ++
                    "author TEXT NOT NULL, " ++
                    "year INTEGER, " ++
                    "isbn TEXT UNIQUE)",
            ok = sqlite3:sql_exec(Pid, Sql),
            sqlite3:close(Pid)
    end.

init([]) ->
    init_book_db(),
    {ok, #state{db_path = 'books.db'}}.

get_all_books() ->
    case gen_server:call(?MODULE, {get_all_books}) of
        {ok, Books} -> {ok, Books};
        Error -> Error
    end.

get_book_by_id(Id) ->
    case gen_server:call(?MODULE, {get_book_by_id, Id}) of
        {ok, Book} -> {ok, Book};
        Error -> Error
    end.

create_book(Attrs) ->
    case gen_server:call(?MODULE, {create_book, Attrs}) of
        {ok, Book} -> {ok, Book};
        Error -> Error
    end.

update_book(Id, Attrs) ->
    case gen_server:call(?MODULE, {update_book, Id, Attrs}) of
        {ok, Book} -> {ok, Book};
        Error -> Error
    end.

delete_book(Id) ->
    case gen_server:call(?MODULE, {delete_book, Id}) of
        ok -> ok;
        Error -> Error
    end.

health_check() ->
    case gen_server:call(?MODULE, health_check) of
        ok -> {ok, healthy};
        Error -> Error
    end.

parse_select_result(Result) ->
    %% Result format for SELECT is: {columns, [ColNames]}, {rows, [[Val1, Val2, ...]]}
    %% or in a list: [{columns, [...]}, {rows, [...]}]
    case Result of
        [{columns, _}, {rows, Rows}] -> Rows;
        {columns, _, {rows, Rows}} -> Rows;  %% tuple format
        {rows, Rows} -> Rows;
        _ -> []
    end.

handle_call({get_all_books}, _From, State) ->
    {ok, Pid} = sqlite3:open(State#state.db_path),
    Sql = "SELECT id, title, author, year, isbn FROM books",
    Result = sqlite3:sql_exec(Pid, Sql),
    sqlite3:close(Pid),
    Rows = parse_select_result(Result),
    Books = lists:map(fun([Id, Title, Author, Year, Isbn]) ->
        #{id => Id, title => Title, author => Author, year => Year, isbn => Isbn}
    end, Rows),
    {reply, {ok, Books}, State};

handle_call({get_book_by_id, Id}, _From, State) ->
    {ok, Pid} = sqlite3:open(State#state.db_path),
    Sql = "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
    Result = sqlite3:sql_exec(Pid, Sql, [Id]),
    sqlite3:close(Pid),
    Rows = parse_select_result(Result),
    case Rows of
        [] -> {reply, {error, not_found}, State};
        [[BookId, Title, Author, Year, Isbn]] ->
            Book = #{id => BookId, title => Title, author => Author, year => Year, isbn => Isbn},
            {reply, {ok, Book}, State}
    end;

handle_call({create_book, Attrs}, _From, State) ->
    Title = maps:get(title, Attrs),
    Author = maps:get(author, Attrs),
    Year = maps:get(year, Attrs, null),
    Isbn = maps:get(isbn, Attrs, null),
    
    case validate_book(Attrs) of
        {error, Reason} -> {reply, {error, Reason}, State};
        ok ->
            {ok, Pid} = sqlite3:open(State#state.db_path),
            Sql = "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            {rowid, _} = sqlite3:sql_exec(Pid, Sql, [Title, Author, Year, Isbn]),
            
            %% Use SELECT with MAX(id) to get the last inserted row
            Sql2 = "SELECT id, title, author, year, isbn FROM books WHERE id = (SELECT MAX(id) FROM books)",
            Result2 = sqlite3:sql_exec(Pid, Sql2),
            sqlite3:close(Pid),
            
            Rows2 = parse_select_result(Result2),
            case Rows2 of
                [[BookId, BookTitle, BookAuthor, BookYear, BookIsbn]] ->
                    Book = #{id => BookId, title => BookTitle, author => BookAuthor, 
                             year => BookYear, isbn => BookIsbn},
                    {reply, {ok, Book}, State};
                _ ->
                    {reply, {error, not_found}, State}
            end
    end;

handle_call({update_book, Id, Attrs}, _From, State) ->
    case get_book_by_id(Id) of
        {error, not_found} -> {reply, {error, not_found}, State};
        {ok, _Book} ->
            Title = maps:get(title, Attrs, undefined),
            Author = maps:get(author, Attrs, undefined),
            Year = maps:get(year, Attrs, undefined),
            Isbn = maps:get(isbn, Attrs, undefined),
            
            {ok, Pid} = sqlite3:open(State#state.db_path),
            case {Title, Author, Year, Isbn} of
                {undefined, undefined, undefined, undefined} ->
                    {reply, {error, no_changes}, State};
                _ ->
                    Updates = lists:flatten([
                        case Title of undefined -> []; _ -> ["title = ?"] end,
                        case Author of undefined -> []; _ -> ["author = ?"] end,
                        case Year of undefined -> []; _ -> ["year = ?"] end,
                        case Isbn of undefined -> []; _ -> ["isbn = ?"] end
                    ]),
                    Params = lists:filter(
                        fun(X) -> X =/= undefined end,
                        [Title, Author, Year, Isbn]
                    ),
                    Sql = "UPDATE books SET " ++ string:join(Updates, ", ") ++ " WHERE id = ?",
                    ParamsWithId = Params ++ [Id],
                    ok = sqlite3:sql_exec(Pid, Sql, ParamsWithId),
                    sqlite3:close(Pid),
                    get_book_by_id(Id)
            end
    end;

handle_call({delete_book, Id}, _From, State) ->
    case get_book_by_id(Id) of
        {error, not_found} -> {reply, {error, not_found}, State};
        {ok, _Book} ->
            {ok, Pid} = sqlite3:open(State#state.db_path),
            Sql = "DELETE FROM books WHERE id = ?",
            ok = sqlite3:sql_exec(Pid, Sql, [Id]),
            sqlite3:close(Pid),
            {reply, ok, State}
    end;

handle_call(health_check, _From, State) ->
    {ok, Pid} = sqlite3:open(State#state.db_path),
    ok = sqlite3:sql_exec(Pid, "SELECT 1"),
    sqlite3:close(Pid),
    {reply, ok, State};

handle_call(_Request, _From, State) ->
    {reply, unknown_request, State}.

handle_cast(_Msg, State) ->
    {noreply, State}.

handle_info(_Info, State) ->
    {noreply, State}.

terminate(_Reason, _State) ->
    ok.

code_change(_OldVsn, State, _Extra) ->
    {ok, State}.

validate_book(Attrs) ->
    case maps:get(title, Attrs, undefined) of
        undefined -> {error, title_required};
        Title when is_binary(Title) orelse is_list(Title) ->
            case maps:get(author, Attrs, undefined) of
                undefined -> {error, author_required};
                Author when is_binary(Author) orelse is_list(Author) ->
                    ok;
                _ -> {error, author_must_be_string}
            end;
        _ -> {error, title_must_be_string}
    end.
