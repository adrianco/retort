%%%-------------------------------------------------------------------
%% @doc book_store: persistence layer for the book collection.
%%
%% Backed by `dets', Erlang/OTP's built-in disk-based term storage
%% (the language-equivalent embedded database to SQLite). The table
%% is owned by this gen_server so its lifetime is tied to the
%% supervision tree.
%%
%% Books are stored as `{Id :: integer(), Book :: map()}' tuples.
%% A separate `{'$next_id', integer()}' entry holds the auto-increment
%% counter so IDs survive restarts.
%%%-------------------------------------------------------------------
-module(book_store).
-behaviour(gen_server).

%% Public API
-export([start_link/0, start_link/1]).
-export([create/1, list/0, list/1, get/1, update/2, delete/1, clear/0]).

%% gen_server callbacks
-export([init/1, handle_call/3, handle_cast/2, handle_info/2,
         terminate/2, code_change/3]).

-define(SERVER, ?MODULE).
-define(TABLE, books_dets).
-define(NEXT_ID_KEY, '$next_id').

%%====================================================================
%% Public API
%%====================================================================

start_link() ->
    start_link("books.dets").

start_link(File) ->
    gen_server:start_link({local, ?SERVER}, ?MODULE, [File], []).

%% @doc Create a new book from a map of attributes. Returns the stored
%% book (including its assigned `id') or `{error, Reason}' on validation
%% failure.
-spec create(map()) -> {ok, map()} | {error, term()}.
create(Attrs) ->
    gen_server:call(?SERVER, {create, Attrs}).

%% @doc List every book.
-spec list() -> [map()].
list() ->
    gen_server:call(?SERVER, list).

%% @doc List books filtered by author (exact match).
-spec list(binary()) -> [map()].
list(Author) ->
    gen_server:call(?SERVER, {list, Author}).

%% @doc Fetch a single book by id.
-spec get(integer()) -> {ok, map()} | {error, not_found}.
get(Id) ->
    gen_server:call(?SERVER, {get, Id}).

%% @doc Update an existing book with the given attributes.
-spec update(integer(), map()) -> {ok, map()} | {error, term()}.
update(Id, Attrs) ->
    gen_server:call(?SERVER, {update, Id, Attrs}).

%% @doc Delete a book by id.
-spec delete(integer()) -> ok | {error, not_found}.
delete(Id) ->
    gen_server:call(?SERVER, {delete, Id}).

%% @doc Remove all books (used by tests).
-spec clear() -> ok.
clear() ->
    gen_server:call(?SERVER, clear).

%%====================================================================
%% gen_server callbacks
%%====================================================================

init([File]) ->
    {ok, _} = dets:open_file(?TABLE, [{file, File}, {type, set}]),
    case dets:lookup(?TABLE, ?NEXT_ID_KEY) of
        [] -> ok = dets:insert(?TABLE, {?NEXT_ID_KEY, 1});
        _ -> ok
    end,
    {ok, #{table => ?TABLE}}.

handle_call({create, Attrs}, _From, State) ->
    case validate(Attrs) of
        ok ->
            Id = next_id(),
            Book = build_book(Id, Attrs),
            ok = dets:insert(?TABLE, {Id, Book}),
            {reply, {ok, Book}, State};
        {error, _} = Err ->
            {reply, Err, State}
    end;

handle_call(list, _From, State) ->
    {reply, all_books(), State};

handle_call({list, Author}, _From, State) ->
    Filtered = [B || B <- all_books(), maps:get(<<"author">>, B) =:= Author],
    {reply, Filtered, State};

handle_call({get, Id}, _From, State) ->
    {reply, lookup(Id), State};

handle_call({update, Id, Attrs}, _From, State) ->
    case lookup(Id) of
        {ok, Existing} ->
            Merged = merge_attrs(Existing, Attrs),
            case validate(Merged) of
                ok ->
                    ok = dets:insert(?TABLE, {Id, Merged}),
                    {reply, {ok, Merged}, State};
                {error, _} = Err ->
                    {reply, Err, State}
            end;
        {error, not_found} = Err ->
            {reply, Err, State}
    end;

handle_call({delete, Id}, _From, State) ->
    case lookup(Id) of
        {ok, _} ->
            ok = dets:delete(?TABLE, Id),
            {reply, ok, State};
        {error, not_found} = Err ->
            {reply, Err, State}
    end;

handle_call(clear, _From, State) ->
    ok = dets:delete_all_objects(?TABLE),
    ok = dets:insert(?TABLE, {?NEXT_ID_KEY, 1}),
    {reply, ok, State};

handle_call(_Request, _From, State) ->
    {reply, {error, unknown_request}, State}.

handle_cast(_Msg, State) ->
    {noreply, State}.

handle_info(_Info, State) ->
    {noreply, State}.

terminate(_Reason, _State) ->
    try dets:close(?TABLE)
    catch _:_ -> ok
    end,
    ok.

code_change(_OldVsn, State, _Extra) ->
    {ok, State}.

%%====================================================================
%% Internal helpers
%%====================================================================

next_id() ->
    Id = dets:update_counter(?TABLE, ?NEXT_ID_KEY, 1) - 1,
    Id.

lookup(Id) ->
    case dets:lookup(?TABLE, Id) of
        [{Id, Book}] -> {ok, Book};
        [] -> {error, not_found}
    end.

all_books() ->
    Books = dets:select(?TABLE, [{{'$1', '$2'},
                                  [{is_integer, '$1'}],
                                  ['$2']}]),
    lists:sort(fun(A, B) -> maps:get(<<"id">>, A) =< maps:get(<<"id">>, B) end,
               Books).

%% Build a normalised book map from raw attributes plus an id.
build_book(Id, Attrs) ->
    #{
        <<"id">> => Id,
        <<"title">> => get_attr(<<"title">>, Attrs, null),
        <<"author">> => get_attr(<<"author">>, Attrs, null),
        <<"year">> => get_attr(<<"year">>, Attrs, null),
        <<"isbn">> => get_attr(<<"isbn">>, Attrs, null)
    }.

%% Merge incoming attributes onto an existing book, preserving the id
%% and keeping known fields normalised.
merge_attrs(Existing, Attrs) ->
    Fields = [<<"title">>, <<"author">>, <<"year">>, <<"isbn">>],
    lists:foldl(
        fun(Field, Acc) ->
            case maps:is_key(Field, Attrs) of
                true -> Acc#{Field => maps:get(Field, Attrs)};
                false -> Acc
            end
        end,
        Existing,
        Fields).

get_attr(Key, Attrs, Default) ->
    case maps:get(Key, Attrs, Default) of
        undefined -> Default;
        Value -> Value
    end.

%% Validation: title and author are required and must be non-empty.
validate(Attrs) ->
    case {present(<<"title">>, Attrs), present(<<"author">>, Attrs)} of
        {true, true} -> ok;
        {false, _} -> {error, <<"title is required">>};
        {_, false} -> {error, <<"author is required">>}
    end.

present(Key, Attrs) ->
    case maps:get(Key, Attrs, undefined) of
        undefined -> false;
        null -> false;
        <<>> -> false;
        Bin when is_binary(Bin) -> string:trim(Bin) =/= <<>>;
        _ -> true
    end.
