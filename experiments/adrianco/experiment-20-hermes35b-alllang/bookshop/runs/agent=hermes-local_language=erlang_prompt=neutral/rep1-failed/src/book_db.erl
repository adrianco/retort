-module(book_db).
-behaviour(gen_server).

%% API
-export([start_link/0, create_book/1, get_all_books/0, get_all_books/1,
         get_book/1, update_book/2, delete_book/1, delete_all/0]).

%% gen_server callbacks
-export([init/1, handle_call/3, handle_cast/2, handle_info/2,
         terminate/2, code_change/3]).

-define(TABLE, book_db).

-record(book, {id, title, author, year, isbn}).

%%-------------------------------------------------------------------
%% API
%%-------------------------------------------------------------------

start_link() ->
    gen_server:start_link({local, ?MODULE}, ?MODULE, [], []).

create_book(Props) ->
    gen_server:call(?MODULE, {create, Props}).

get_all_books() ->
    gen_server:call(?MODULE, {get_all, undefined}).

get_all_books(Author) ->
    gen_server:call(?MODULE, {get_all, Author}).

get_book(Id) ->
    gen_server:call(?MODULE, {get, Id}).

update_book(Id, Props) ->
    gen_server:call(?MODULE, {update, Id, Props}).

delete_book(Id) ->
    gen_server:call(?MODULE, {delete, Id}).

delete_all() ->
    gen_server:call(?MODULE, delete_all).

%%-------------------------------------------------------------------
%% gen_server callbacks
%%-------------------------------------------------------------------

init([]) ->
    try ets:delete(?TABLE) of
        true -> ok;
        false -> ok
    catch
        _:_ -> ok
    end,
    Table = ets:new(?TABLE, [named_table, set, public]),
    {ok, #{table => Table, next_id => 1}}.

handle_call({create, Props}, _From, #{table := Table, next_id := Id} = State) ->
    Book = #book{
        id = Id,
        title = maps:get(title, Props, ""),
        author = maps:get(author, Props, ""),
        year = maps:get(year, Props, undefined),
        isbn = maps:get(isbn, Props, "")
    },
    case validate(Book) of
        ok ->
            ets:insert(Table, Book),
            {reply, {ok, map_from_record(Book)}, State#{next_id := Id + 1}};
        {error, Reason} ->
            {reply, {error, Reason}, State}
    end;

handle_call({get_all, undefined}, _From, #{table := Table} = State) ->
    Books = [map_from_record(B) || B <- ets:tab2list(Table)],
    {reply, {ok, Books}, State};

handle_call({get_all, Author}, _From, #{table := Table} = State) ->
    Books = [map_from_record(B) || B <- ets:tab2list(Table), B#book.author =:= Author],
    {reply, {ok, Books}, State};

handle_call({get, Id}, _From, #{table := Table} = State) ->
    Result = case ets:lookup(Table, Id) of
        [#book{id = Id} = Book] -> {ok, map_from_record(Book)};
        [] -> {error, not_found}
    end,
    {reply, Result, State};

handle_call({update, Id, Props}, _From, #{table := Table} = State) ->
    case ets:lookup(Table, Id) of
        [#book{} = Book] ->
            Updated = update_fields(Book, Props),
            case validate(Updated) of
                ok ->
                    ets:insert(Table, Updated),
                    {reply, {ok, map_from_record(Updated)}, State};
                {error, Reason} ->
                    {reply, {error, Reason}, State}
            end;
        [] ->
            {reply, {error, not_found}, State}
    end;

handle_call({delete, Id}, _From, #{table := Table} = State) ->
    case ets:lookup(Table, Id) of
        [#book{}] ->
            ets:delete(Table, Id),
            {reply, {ok, deleted}, State};
        [] ->
            {reply, {error, not_found}, State}
    end;

handle_call(delete_all, _From, #{table := Table} = State) ->
    ets:delete_all_objects(Table),
    {reply, ok, State};

handle_call(_Request, _From, State) ->
    {reply, {error, unknown_request}, State}.

handle_cast(_Msg, State) ->
    {noreply, State}.

handle_info(_Info, State) ->
    {noreply, State}.

terminate(_Reason, #{table := Table}) ->
    catch ets:delete(Table),
    ok.

code_change(_OldVsn, State, _Extra) ->
    {ok, State}.

%%-------------------------------------------------------------------
%% Internal functions
%%-------------------------------------------------------------------

map_from_record(#book{id=Id, title=Title, author=Author, year=Year, isbn=ISBN}) ->
    Base = #{id => Id, title => Title, author => Author},
    case Year of
        undefined -> Base#{isbn => ISBN};
        _ -> Base#{year => Year, isbn => ISBN}
    end.

validate(#book{title = T, author = A}) when is_list(T) ->
    case T of
        undefined -> {error, "title is required"};
        "" -> {error, "title is required"};
        _ ->
            case A of
                undefined -> {error, "author is required"};
                "" -> {error, "author is required"};
                _ -> ok
            end
    end;

validate(#book{title = T, author = A}) when is_binary(T), is_binary(A) ->
    validate(#book{title = binary_to_list(T), author = binary_to_list(A)});

validate(_) ->
    {error, "invalid book data"}.

update_fields(Book, Props) ->
    Book#book{
        title = maps:get(title, Props, Book#book.title),
        author = maps:get(author, Props, Book#book.author),
        year = maps:get(year, Props, Book#book.year),
        isbn = maps:get(isbn, Props, Book#book.isbn)
    }.
