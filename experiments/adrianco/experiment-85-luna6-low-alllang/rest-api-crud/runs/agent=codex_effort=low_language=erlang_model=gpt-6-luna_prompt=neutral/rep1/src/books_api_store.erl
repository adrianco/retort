-module(books_api_store).
-behaviour(gen_server).
-export([start_link/0, stop/0, create/1, list/1, get/1, update/2, delete/1]).
-export([init/1, handle_call/3, handle_cast/2, handle_info/2, terminate/2, code_change/3]).

start_link() -> gen_server:start_link({local, ?MODULE}, ?MODULE, [], []).
stop() -> gen_server:stop(?MODULE).
create(Book) -> gen_server:call(?MODULE, {create, Book}).
list(Author) -> gen_server:call(?MODULE, {list, Author}).
get(Id) -> gen_server:call(?MODULE, {get, Id}).
update(Id, Book) -> gen_server:call(?MODULE, {update, Id, Book}).
delete(Id) -> gen_server:call(?MODULE, {delete, Id}).

init([]) ->
    Db = application:get_env(books_api, database, "books.db"),
    _ = query(Db, "CREATE TABLE IF NOT EXISTS books (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, author TEXT NOT NULL, year INTEGER, isbn TEXT);"),
    {ok, #{db => Db}}.
handle_call({create, Book}, _From, S=#{db := Db}) ->
    Sql = lists:flatten(io_lib:format("INSERT INTO books(title,author,year,isbn) VALUES(~s,~s,~s,~s); SELECT json_object('id',last_insert_rowid(),'title',~s,'author',~s,'year',~s,'isbn',~s) AS book;", [sql(maps:get(<<"title">>,Book)),sql(maps:get(<<"author">>,Book)),sql_value(maps:get(<<"year">>,Book, null)),sql(maps:get(<<"isbn">>,Book, null)),sql(maps:get(<<"title">>,Book)),sql(maps:get(<<"author">>,Book)),sql_value(maps:get(<<"year">>,Book,null)),sql(maps:get(<<"isbn">>,Book,null))])),
    {reply, one(query(Db, Sql)), S};
handle_call({list, Author}, _From, S=#{db := Db}) ->
    Where = case Author of undefined -> ""; _ -> " WHERE author=" ++ sql(Author) end,
    {reply, rows(query(Db, "SELECT json_object('id',id,'title',title,'author',author,'year',year,'isbn',isbn) AS book FROM books" ++ Where ++ " ORDER BY id;")), S};
handle_call({get, Id}, _From, S=#{db := Db}) -> {reply, one(query(Db, row_sql(Id))), S};
handle_call({update, Id, Book}, _From, S=#{db := Db}) ->
    Sql = "UPDATE books SET title=" ++ sql(maps:get(<<"title">>,Book)) ++ ",author=" ++ sql(maps:get(<<"author">>,Book)) ++ ",year=" ++ sql_value(maps:get(<<"year">>,Book,null)) ++ ",isbn=" ++ sql(maps:get(<<"isbn">>,Book,null)) ++ " WHERE id=" ++ integer_to_list(Id) ++ "; " ++ row_sql(Id),
    {reply, one(query(Db, Sql)), S};
handle_call({delete, Id}, _From, S=#{db := Db}) ->
    {reply, query(Db, "DELETE FROM books WHERE id=" ++ integer_to_list(Id) ++ "; SELECT changes() AS changes;"), S};
handle_call(_, _From, S) -> {reply, {error, bad_request}, S}.
handle_cast(_, S) -> {noreply, S}.
handle_info(_, S) -> {noreply, S}.
terminate(_, _) -> ok.
code_change(_, S, _) -> {ok, S}.

row_sql(Id) -> "SELECT json_object('id',id,'title',title,'author',author,'year',year,'isbn',isbn) AS book FROM books WHERE id=" ++ integer_to_list(Id) ++ ";".
query(Db, Sql) ->
    Port = open_port({spawn_executable, os:find_executable("sqlite3")}, [binary, exit_status, use_stdio, stderr_to_stdout, {args, ["-json", Db, Sql]}]),
    collect(Port, <<>>).
collect(Port, Acc) -> receive
    {Port, {data, Data}} -> collect(Port, <<Acc/binary, Data/binary>>);
    {Port, {exit_status, 0}} -> decode(Acc);
    {Port, {exit_status, _}} -> {error, Acc}
end.
decode(Bin) ->
    Trim = string:trim(binary_to_list(Bin)),
    case Trim of [] -> []; _ -> try jsx:decode(list_to_binary(Trim), [return_maps]) catch _:_ -> [] end end.
rows({error, _}=E) -> E;
rows(L) when is_list(L) -> [decode_row(R) || R <- L];
rows(_) -> [].
one({error,_}=E) -> E;
one([R|_]) -> decode_row(R);
one(_) -> not_found.
decode_row(#{<<"book">> := B}) -> try jsx:decode(B, [return_maps]) catch _:_ -> #{} end;
decode_row(#{<<"changes">> := C}) -> #{<<"changes">> => C};
decode_row(M) when is_map(M) -> M;
decode_row(X) -> X.
sql(null) -> "NULL";
sql(undefined) -> "NULL";
sql(V) -> "'" ++ lists:flatten(string:replace(lists:flatten(io_lib:format("~ts", [V])), "'", "''", all)) ++ "'".
sql_value(null) -> "NULL";
sql_value(undefined) -> "NULL";
sql_value(V) when is_integer(V) -> integer_to_list(V);
sql_value(V) -> sql(V).
