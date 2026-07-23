-module(book_api_db).
-behaviour(gen_server).

-export([start_link/0, init/1, handle_call/3, handle_cast/2, handle_info/2, terminate/2, code_change/3]).
-export([init_db/0, get_all_books/0, get_book_by_id/1, create_book/1, update_book/2, delete_book/1, reset_db/0]).

start_link() ->
    gen_server:start_link({local, ?MODULE}, ?MODULE, [], []).

init([]) ->
    {ok, init_db()}.

init_db() ->
    %% Create ETS table for books
    case ets:info(books) of
        undefined ->
            ets:new(books, [named_table, public, {keypos, 2}]);
        _ ->
            ok
    end,
    %% Load any existing data from a file if it exists
    load_from_file(),
    ok.

reset_db() ->
    ets:delete(books),
    init_db().

get_all_books() ->
    case ets:info(books) of
        undefined ->
            {error, db_not_initialized};
        _ ->
            {ok, ets:tab2list(books)}
    end.

get_book_by_id(Id) when is_integer(Id) ->
    case ets:info(books) of
        undefined ->
            {error, db_not_initialized};
        _ ->
            case ets:lookup(books, Id) of
                [Book] -> {ok, Book};
                [] -> {error, not_found}
            end
    end;
get_book_by_id(_Id) ->
    {error, invalid_id}.

create_book(#{title := Title, author := Author} = Book) ->
    case ets:info(books) of
        undefined ->
            {error, db_not_initialized};
        _ ->
            %% Generate a new ID
            NextId = case ets:info(books, size) of
                0 -> 1;
                Size -> Size + 1
            end,
            Year = maps:get(year, Book, null),
            ISBN = maps:get(isbn, Book, null),
            NewBook = #{
                id => NextId,
                title => Title,
                author => Author,
                year => Year,
                isbn => ISBN
            },
            ets:insert(books, {NextId, NewBook}),
            save_to_file(),
            {ok, NewBook}
    end;
create_book(_) ->
    {error, invalid_data}.

update_book(Id, Book) when is_integer(Id) ->
    case ets:info(books) of
        undefined ->
            {error, db_not_initialized};
        _ ->
            case ets:lookup(books, Id) of
                [] ->
                    {error, not_found};
                [_OldBook] ->
                    %% Get existing book
                    [ExistingBook] = ets:lookup(books, Id),
                    %% Merge the new data
                    UpdatedBook = maps:merge(ExistingBook, Book),
                    %% Update the ETS table
                    ets:insert(books, {Id, UpdatedBook}),
                    save_to_file(),
                    {ok, UpdatedBook}
            end
    end;
update_book(_Id, _Book) ->
    {error, invalid_id}.

delete_book(Id) when is_integer(Id) ->
    case ets:info(books) of
        undefined ->
            {error, db_not_initialized};
        _ ->
            case ets:lookup(books, Id) of
                [] ->
                    {error, not_found};
                [_Book] ->
                    ets:delete(books, Id),
                    save_to_file(),
                    {ok, deleted}
            end
    end;
delete_book(_Id) ->
    {error, invalid_id}.

%% Save ETS data to file for persistence
save_to_file() ->
    case ets:info(books) of
        undefined ->
            ok;
        _ ->
            BooksList = ets:tab2list(books),
            %% Convert to a format that can be serialized
            Data = [{Id, book_to_json(Book)} || {Id, Book} <- BooksList],
            %% Write to a file
            DataStr = io_lib:format("~p.", [Data]),
            %% Try to write to priv directory first
            case save_to_priv(DataStr) of
                ok ->
                    ok;
                _ ->
                    %% Fallback to temporary location
                    file:write_file("/tmp/book_api_books.dat", DataStr)
            end
    end,
    ok.

save_to_priv(DataStr) ->
    try
        %% Try to create the priv directory
        PrivDir = filename:join([code:base_dir(application, book_api), "priv"]),
        file:ensure_dir(PrivDir),
        File = filename:join([PrivDir, "books.dat"]),
        file:write_file(File, DataStr)
    catch
        _:_ ->
            error
    end.

%% Load data from file on startup
load_from_file() ->
    %% Try to load from priv directory first
    case load_from_priv() of
        ok ->
            ok;
        _ ->
            %% Fallback to temporary location
            File = "/tmp/book_api_books.dat",
            case file:read_file(File) of
                {ok, Content} ->
                    case io_lib:read_term(list_to_binary(Content), []) of
                        {ok, Data} when is_list(Data) ->
                            ets:insert(books, [{Id, json_to_book(Book)} || {Id, Book} <- Data]);
                        _ ->
                            ok
                    end;
                {error, enoent} ->
                    ok
            end
    end,
    ok.

load_from_priv() ->
    try
        PrivDir = filename:join([code:base_dir(application, book_api), "priv"]),
        File = filename:join([PrivDir, "books.dat"]),
        case file:read_file(File) of
            {ok, Content} ->
                case io_lib:read_term(list_to_binary(Content), []) of
                    {ok, Data} when is_list(Data) ->
                        ets:insert(books, [{Id, json_to_book(Book)} || {Id, Book} <- Data]);
                    _ ->
                        ok
                end;
            {error, enoent} ->
                ok
        end
    catch
        _:_ ->
            error
    end.

%% Helper functions to convert between book maps and JSON format for file storage
book_to_json(Book) ->
    #{
        <<"id">> => maps:get(id, Book, null),
        <<"title">> => maps:get(title, Book),
        <<"author">> => maps:get(author, Book),
        <<"year">> => maps:get(year, Book, null),
        <<"isbn">> => maps:get(isbn, Book, null)
    }.

json_to_book(Json) ->
    #{
        id => maps:get(<<"id">>, Json, undefined),
        title => maps:get(<<"title">>, Json),
        author => maps:get(<<"author">>, Json),
        year => maps:get(<<"year">>, Json, null),
        isbn => maps:get(<<"isbn">>, Json, null)
    }.

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
