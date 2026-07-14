-module(bookapi_db).

-behaviour(gen_server).

%% API
-export([start_link/0, get_book/1, create_book/1, update_book/2, delete_book/1, list_books/0, list_books/1]).
%% gen_server callbacks
-export([init/1, handle_call/3, handle_cast/2, handle_info/2, terminate/2, code_change/3]).

-record(book, {id, title, author, year, isbn}).

start_link() ->
    gen_server:start_link({local, ?MODULE}, ?MODULE, [], []).

get_book(Id) ->
    gen_server:call(?MODULE, {get, Id}).

create_book(Data) ->
    gen_server:call(?MODULE, {create, Data}).

update_book(Id, Data) ->
    gen_server:call(?MODULE, {update, Id, Data}).

delete_book(Id) ->
    gen_server:call(?MODULE, {delete, Id}).

list_books() ->
    gen_server:call(?MODULE, list).

list_books(Author) ->
    gen_server:call(?MODULE, {list, author, Author}).

init([]) ->
    _Table = ets:new(book_table, [set, named_table, public]),
    SeedBooks = [
        #{title => "The Great Gatsby", author => "F. Scott Fitzgerald", year => 1925, isbn => "978-0743273565"},
        #{title => "To Kill a Mockingbird", author => "Harper Lee", year => 1960, isbn => "978-0061120084"},
        #{title => "1984", author => "George Orwell", year => 1949, isbn => "978-0451524935"}
    ],
    NextId = insert_seeds(SeedBooks, 1),
    {ok, #{next_id => NextId}}.

insert_seeds(Books, NextId) ->
    case Books of
        [] -> NextId;
        [BookData | Rest] ->
            Book = #book{id = NextId,
                         title = maps:get(title, BookData),
                         author = maps:get(author, BookData),
                         year = maps:get(year, BookData),
                         isbn = maps:get(isbn, BookData)},
            ets:insert(book_table, Book),
            insert_seeds(Rest, NextId + 1)
    end.

handle_call({get, Id}, _From, State) ->
    case ets:lookup(book_table, Id) of
        [#book{id = Id, title = Title, author = Author, year = Year, isbn = Isbn}] ->
            Result = #{id => Id, title => Title, author => Author, year => Year, isbn => Isbn},
            {reply, {ok, Result}, State};
        [] ->
            {reply, {error, not_found}, State}
    end;

handle_call({create, Data}, _From, State) ->
    case bookapi_validator:validate_create(Data) of
        {ok, Validated} ->
            NextId = maps:get(next_id, State),
            Book = #book{id = NextId,
                         title = maps:get(title, Validated),
                         author = maps:get(author, Validated),
                         year = maps:get(year, Validated),
                         isbn = maps:get(isbn, Validated)},
            ets:insert(book_table, Book),
            Result = #{id => NextId, title => maps:get(title, Validated),
                       author => maps:get(author, Validated),
                       year => maps:get(year, Validated),
                       isbn => maps:get(isbn, Validated)},
            {reply, {ok, Result}, State#{next_id => NextId + 1}};
        {error, Reason} ->
            {reply, {error, Reason}, State}
    end;

handle_call({update, Id, Data}, _From, State) ->
    case ets:lookup(book_table, Id) of
        [#book{id = Id, title = Title, author = Author, year = Year, isbn = Isbn} = OldBook] ->
            Validated = validate_update_fields(OldBook, Data),
            case bookapi_validator:validate_update(Validated, maps:size(Data)) of
                {ok, Updated} ->
                    Book = OldBook#book{
                        title = maps:get(title, Updated, Title),
                        author = maps:get(author, Updated, Author),
                        year = maps:get(year, Updated, Year),
                        isbn = maps:get(isbn, Updated, Isbn)
                    },
                    ets:insert(book_table, Book),
                    UpdatedResult = #{id => Id, title => maps:get(title, Updated, Title),
                                      author => maps:get(author, Updated, Author),
                                      year => maps:get(year, Updated, Year),
                                      isbn => maps:get(isbn, Updated, Isbn)},
                    {reply, {ok, UpdatedResult}, State};
                {error, Reason} ->
                    {reply, {error, Reason}, State}
            end;
        [] ->
            {reply, {error, not_found}, State}
    end;

handle_call({delete, Id}, _From, State) ->
    case ets:delete(book_table, Id) of
        true ->
            {reply, {ok, deleted}, State};
        false ->
            {reply, {error, not_found}, State}
    end;

handle_call(list, _From, State) ->
    Books = ets:tab2list(book_table),
    Result = lists:map(fun(#book{id = BookId, title = T, author = A, year = Y, isbn = I}) ->
        #{id => BookId, title => T, author => A, year => Y, isbn => I}
    end, Books),
    {reply, Result, State};

handle_call({list, author, AuthorName}, _From, State) ->
    Books = ets:tab2list(book_table),
    Filtered = lists:filter(fun(#book{author = Au}) ->
        Au =:= AuthorName
    end, Books),
    Formatted = lists:map(fun(#book{id = BookId, title = T, author = Au, year = Y, isbn = I}) ->
        #{id => BookId, title => T, author => Au, year => Y, isbn => I}
    end, Filtered),
    {reply, Formatted, State};

handle_call(_Request, _From, State) ->
    {reply, {error, unknown_request}, State}.

validate_update_fields(Book, Data) ->
    maps:merge(
        #{title => Book#book.title, author => Book#book.author, year => Book#book.year, isbn => Book#book.isbn},
        maps:with([title, author, year, isbn], Data)
    ).

handle_cast(_Msg, State) ->
    {noreply, State}.

handle_info(_Info, State) ->
    {noreply, State}.

terminate(_Reason, _State) ->
    ok.

code_change(_OldVsn, State, _Extra) ->
    {ok, State}.
