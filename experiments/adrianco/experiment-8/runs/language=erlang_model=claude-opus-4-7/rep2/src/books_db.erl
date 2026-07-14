-module(books_db).
-behaviour(gen_server).

-export([start_link/0]).
-export([create/1, list/0, list/1, get/1, update/2, delete/1, clear/0]).
-export([init/1, handle_call/3, handle_cast/2, handle_info/2,
         terminate/2, code_change/3]).

-define(TABLE, books_table).

start_link() ->
    gen_server:start_link({local, ?MODULE}, ?MODULE, [], []).

create(Book) ->
    gen_server:call(?MODULE, {create, Book}).

list() ->
    gen_server:call(?MODULE, list_all).

list(Author) ->
    gen_server:call(?MODULE, {list_by_author, Author}).

get(Id) ->
    gen_server:call(?MODULE, {get, Id}).

update(Id, Updates) ->
    gen_server:call(?MODULE, {update, Id, Updates}).

delete(Id) ->
    gen_server:call(?MODULE, {delete, Id}).

clear() ->
    gen_server:call(?MODULE, clear).

init([]) ->
    File = application:get_env(books, db_file, "books.dets"),
    ok = filelib:ensure_dir(File),
    {ok, ?TABLE} = dets:open_file(?TABLE, [{file, File}, {type, set}]),
    {ok, #{}}.

handle_call({create, Book}, _From, State) ->
    Id = generate_id(),
    NewBook = Book#{id => Id},
    ok = dets:insert(?TABLE, {Id, NewBook}),
    {reply, {ok, NewBook}, State};

handle_call(list_all, _From, State) ->
    Books = [B || {_Id, B} <- dets:match_object(?TABLE, '_')],
    {reply, {ok, Books}, State};

handle_call({list_by_author, Author}, _From, State) ->
    Books = [B || {_Id, B} <- dets:match_object(?TABLE, '_'),
                  maps:get(author, B, undefined) =:= Author],
    {reply, {ok, Books}, State};

handle_call({get, Id}, _From, State) ->
    case dets:lookup(?TABLE, Id) of
        [{Id, Book}] -> {reply, {ok, Book}, State};
        [] -> {reply, {error, not_found}, State}
    end;

handle_call({update, Id, Updates}, _From, State) ->
    case dets:lookup(?TABLE, Id) of
        [{Id, Book}] ->
            Updated = maps:merge(Book, Updates),
            Updated2 = Updated#{id => Id},
            ok = dets:insert(?TABLE, {Id, Updated2}),
            {reply, {ok, Updated2}, State};
        [] ->
            {reply, {error, not_found}, State}
    end;

handle_call({delete, Id}, _From, State) ->
    case dets:lookup(?TABLE, Id) of
        [{Id, _}] ->
            ok = dets:delete(?TABLE, Id),
            {reply, ok, State};
        [] ->
            {reply, {error, not_found}, State}
    end;

handle_call(clear, _From, State) ->
    ok = dets:delete_all_objects(?TABLE),
    {reply, ok, State};

handle_call(_Msg, _From, State) ->
    {reply, {error, unknown_call}, State}.

handle_cast(_Msg, State) ->
    {noreply, State}.

handle_info(_Info, State) ->
    {noreply, State}.

terminate(_Reason, _State) ->
    _ = dets:close(?TABLE),
    ok.

code_change(_OldVsn, State, _Extra) ->
    {ok, State}.

generate_id() ->
    Int = erlang:unique_integer([positive, monotonic]),
    integer_to_binary(Int).
