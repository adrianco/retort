-module(books_store).
-behaviour(gen_server).

-export([start_link/1, create/1, list/1, get/1, update/2, delete/1]).
-export([init/1, handle_call/3, handle_cast/2, handle_info/2, terminate/2, code_change/3]).

-define(TABLE, books).
-record(state, {db_path}).

start_link(DbPath) -> gen_server:start_link({local, ?MODULE}, ?MODULE, DbPath, []).
create(Book) -> gen_server:call(?MODULE, {create, Book}, infinity).
list(Author) -> gen_server:call(?MODULE, {list, Author}, infinity).
get(Id) -> gen_server:call(?MODULE, {get, Id}, infinity).
update(Id, Book) -> gen_server:call(?MODULE, {update, Id, Book}, infinity).
delete(Id) -> gen_server:call(?MODULE, {delete, Id}, infinity).

init(DbPath0) ->
    DbPath = path_list(DbPath0),
    ok = ensure_schema(DbPath),
    {ok, #state{db_path = DbPath}}.

handle_call({create, Book}, _From, State = #state{db_path = Db}) ->
    Fields = fields(Book),
    Sql = ["INSERT INTO books (title,author,year,isbn) VALUES (",
           sql_value(maps:get(title, Fields)), ",", sql_value(maps:get(author, Fields)), ",",
           sql_value(maps:get(year, Fields)), ",", sql_value(maps:get(isbn, Fields)), ");",
           "SELECT json_object('id',id,'title',title,'author',author,'year',year,'isbn',isbn) AS book FROM books WHERE id=last_insert_rowid();"],
    Reply = case query(Db, Sql) of
                {ok, [Line | _]} -> decode_book(Line);
                Error -> Error
            end,
    {reply, Reply, State};
handle_call({list, Author}, _From, State = #state{db_path = Db}) ->
    Where = case Author of undefined -> ""; _ -> [" WHERE author = ", sql_value(Author)] end,
    Sql = ["SELECT json_group_array(json_object('id',id,'title',title,'author',author,'year',year,'isbn',isbn)) FROM books",
           Where, ";"],
    Reply = case query(Db, Sql) of
                {ok, [Line | _]} -> decode_books(Line);
                Error -> Error
            end,
    {reply, Reply, State};
handle_call({get, Id}, _From, State = #state{db_path = Db}) ->
    Reply = select_one(Db, Id),
    {reply, Reply, State};
handle_call({update, Id, Book}, _From, State = #state{db_path = Db}) ->
    Fields = fields(Book),
    Sql = ["UPDATE books SET title=", sql_value(maps:get(title, Fields)),
           ",author=", sql_value(maps:get(author, Fields)), ",year=", sql_value(maps:get(year, Fields)),
           ",isbn=", sql_value(maps:get(isbn, Fields)), " WHERE id=", integer_to_list(Id), ";",
           "SELECT changes() AS changes;"],
    Reply = case query(Db, Sql) of
                {ok, [Line | _]} -> case books_json:decode(Line) of {ok, [#{<<"changes">> := 1}]} -> select_one(Db, Id); _ -> {error, not_found} end;
                {ok, _} -> {error, not_found};
                Error -> Error
            end,
    {reply, Reply, State};
handle_call({delete, Id}, _From, State = #state{db_path = Db}) ->
    Sql = ["DELETE FROM books WHERE id=", integer_to_list(Id), ";SELECT changes() AS changes;"],
    Reply = case query(Db, Sql) of
                {ok, [Line | _]} -> case books_json:decode(Line) of {ok, [#{<<"changes">> := 1}]} -> {ok, deleted}; _ -> {error, not_found} end;
                {ok, _} -> {error, not_found};
                Error -> Error
            end,
    {reply, Reply, State};
handle_call(_Request, _From, State) -> {reply, {error, bad_request}, State}.

handle_cast(_Msg, State) -> {noreply, State}.
handle_info(_Info, State) -> {noreply, State}.
terminate(_Reason, _State) -> ok.
code_change(_Old, State, _Extra) -> {ok, State}.

ensure_schema(Db) ->
    case query(Db, "CREATE TABLE IF NOT EXISTS books (id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,author TEXT NOT NULL,year INTEGER,isbn TEXT);") of
        {ok, _} -> ok;
        {error, Reason} -> erlang:error({sqlite_setup_failed, Reason})
    end.

select_one(Db, Id) ->
    Sql = ["SELECT json_object('id',id,'title',title,'author',author,'year',year,'isbn',isbn) AS book FROM books WHERE id=", integer_to_list(Id), ";"],
    case query(Db, Sql) of
        {ok, [Line | _]} -> decode_book(Line);
        {ok, []} -> {error, not_found};
        Error -> Error
    end.

fields(Book) ->
    #{title => maps:get(<<"title">>, Book), author => maps:get(<<"author">>, Book),
      year => maps:get(<<"year">>, Book, null), isbn => maps:get(<<"isbn">>, Book, null)}.

query(Db, Sql) ->
    SqlBin = iolist_to_binary(Sql),
    case os:find_executable("sqlite3") of
        false -> {error, sqlite3_not_found};
        Executable ->
            Port = open_port({spawn_executable, Executable},
                             [binary, exit_status, use_stdio, stderr_to_stdout,
                              {args, ["-json", Db, binary_to_list(SqlBin)]}]),
            collect(Port, <<>>)
    end.

collect(Port, Acc) ->
    receive
        {Port, {data, Data}} -> collect(Port, <<Acc/binary, Data/binary>>);
        {Port, {exit_status, 0}} ->
            Lines = [string:trim(binary_to_list(L)) || L <- binary:split(Acc, <<"\n">>, [global]), byte_size(L) > 0],
            {ok, Lines};
        {Port, {exit_status, Status}} -> {error, {sqlite_error, Status, binary_to_list(Acc)}}
    after 10000 ->
        port_close(Port),
        {error, sqlite_timeout}
    end.

decode_book(Line) ->
    case books_json:decode(Line) of
        {ok, [Row]} when is_map(Row) -> unwrap_row(Row);
        {ok, Book} when is_map(Book) -> {ok, Book};
        Error -> Error
    end.
decode_books(Line) ->
    case books_json:decode(Line) of
        {ok, [#{<<"json_group_array(json_object('id',id,'title',title,'author',author,'year',year,'isbn',isbn))">> := Value}]} ->
            case books_json:decode(Value) of {ok, Books} when is_list(Books) -> {ok, Books}; Error -> Error end;
        {ok, Books} when is_list(Books) -> {ok, Books};
                                    {ok, null} -> {ok, []}; Error -> Error end.

unwrap_row(Row) ->
    [{_Key, Value}] = maps:to_list(Row),
    case books_json:decode(Value) of {ok, Book} when is_map(Book) -> {ok, Book}; Error -> Error end.

sql_value(null) -> "NULL";
sql_value(undefined) -> "NULL";
sql_value(Value) when is_integer(Value) -> integer_to_list(Value);
sql_value(Value) when is_float(Value) -> io_lib:format("~p", [Value]);
sql_value(Value) when is_binary(Value) -> sql_string(binary_to_list(Value));
sql_value(Value) when is_list(Value) -> sql_string(Value);
sql_value(_) -> "NULL".

sql_string(Value) -> ["'", lists:flatten([case C of $' -> "''"; _ -> [C] end || C <- Value]), "'"] .
path_list(Path) when is_binary(Path) -> binary_to_list(Path);
path_list(Path) when is_list(Path) -> Path.
