-module(books_db).
-behaviour(gen_server).
-export([start_link/1, create/1, list/1, get/1, update/2, delete/1]).
-export([init/1, handle_call/3, handle_cast/2, handle_info/2, terminate/2, code_change/3]).

start_link(Path) -> gen_server:start_link({local, ?MODULE}, ?MODULE, Path, []).
create(Book) -> gen_server:call(?MODULE, {create, Book}).
list(Author) -> gen_server:call(?MODULE, {list, Author}).
get(Id) -> gen_server:call(?MODULE, {get, Id}).
update(Id, Book) -> gen_server:call(?MODULE, {update, Id, Book}).
delete(Id) -> gen_server:call(?MODULE, {delete, Id}).

init(Path) ->
    _ = query(Path, "CREATE TABLE IF NOT EXISTS books (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, author TEXT NOT NULL, year INTEGER, isbn TEXT);"),
    {ok, #{path => Path}}.

handle_call({create, B}, _From, S=#{path:=P}) ->
    Sql = lists:flatten(io_lib:format("INSERT INTO books(title,author,year,isbn) VALUES(~s,~s,~s,~s); SELECT id,title,author,year,isbn FROM books WHERE id=last_insert_rowid();",
      [q(maps:get(title,B)), q(maps:get(author,B)), v(maps:get(year,B,null)), q(maps:get(isbn,B,<<>>))])),
    {reply, query(P, Sql), S};
handle_call({list,A}, _From, S=#{path:=P}) ->
    Where = case A of undefined -> ""; _ -> " WHERE author="++q(A) end,
    {reply, query_list(P, "SELECT id,title,author,year,isbn FROM books"++Where++";"), S};
handle_call({get,I}, _From, S=#{path:=P}) -> {reply, query(P, select(" WHERE id="++integer_to_list(I))), S};
handle_call({update,I,B}, _From, S=#{path:=P}) ->
    Sql = lists:flatten(io_lib:format("UPDATE books SET title=~s,author=~s,year=~s,isbn=~s WHERE id=~B; SELECT changes();", [q(maps:get(title,B)),q(maps:get(author,B)),v(maps:get(year,B,null)),q(maps:get(isbn,B,<<>>)),I])),
    case query(P,Sql) of {ok,_} -> case query(P, "SELECT id,title,author,year,isbn FROM books WHERE id="++integer_to_list(I)++";") of {ok,[]}->{reply,not_found,S}; Result->{reply,Result,S} end; E->{reply,E,S} end;
handle_call({delete,I}, _From, S=#{path:=P}) ->
    case query(P,"SELECT id FROM books WHERE id="++integer_to_list(I)++";") of
        {ok,[]}->{reply,not_found,S}; {ok,_}->case query(P,"DELETE FROM books WHERE id="++integer_to_list(I)++";") of {ok,_}->{reply,ok,S}; E->{reply,E,S} end; E->{reply,E,S}
    end;
handle_call(_,_,S)->{reply,{error,bad_request},S}.
handle_cast(_,S)->{noreply,S}.
handle_info(_,S)->{noreply,S}.
terminate(_,_) -> ok.
code_change(_,S,_)->{ok,S}.

select(Suffix)->"SELECT id,title,author,year,isbn FROM books"++Suffix++";".
query(Path,Sql)->
    Cmd="sqlite3 -json "++shellq(Path)++" "++shellq(Sql),
    Out=string:trim(os:cmd(Cmd)),
    case Out of []->{ok,[]}; _ -> try jsx:decode(list_to_binary(Out),[return_maps]) of [One]->{ok,keys(One)}; Many when is_list(Many)->{ok,[keys(X)||X<-Many]}; Other->{ok,keys(Other)} catch _:_->{error,database_error} end end.
query_list(Path,Sql)->
    Cmd="sqlite3 -json "++shellq(Path)++" "++shellq(Sql),
    Out=string:trim(os:cmd(Cmd)),
    case Out of []->{ok,[]}; _ -> try jsx:decode(list_to_binary(Out),[return_maps]) of L when is_list(L)->{ok,[keys(X)||X<-L]}; M when is_map(M)->{ok,[keys(M)]} catch _:_->{error,database_error} end end.
keys(M)->maps:from_list([{binary_to_atom(K,utf8),V}||{K,V}<-maps:to_list(M)]).
q(B) when is_binary(B)->q(binary_to_list(B));
q(L) when is_list(L)->"'"++lists:flatten(string:replace(L,"'","''",all))++"'";
q(V)->q(lists:flatten(io_lib:format("~p",[V]))).
v(null)->"NULL"; v(I) when is_integer(I)->integer_to_list(I); v(X)->q(X).
shellq(B) when is_binary(B)->shellq(binary_to_list(B));
shellq(L)->"'"++lists:flatten(string:replace(L,"'","'\\''",all))++"'".
