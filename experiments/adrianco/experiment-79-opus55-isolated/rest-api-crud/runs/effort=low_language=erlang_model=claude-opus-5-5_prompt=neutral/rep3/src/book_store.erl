%% Persistent book storage backed by DETS, OTP's embedded on-disk database.
%% All access is serialised through this gen_server.
-module(book_store).
-behaviour(gen_server).

-export([start_link/1, create/1, list/0, list/1, get/1, update/2, delete/1, clear/0]).
-export([init/1, handle_call/3, handle_cast/2, terminate/2]).

-define(TABLE, book_store_table).
-define(COUNTER, '$next_id').

-type book() :: #{
    id := pos_integer(),
    title := binary(),
    author := binary(),
    year := integer() | null,
    isbn := binary() | null
}.
-export_type([book/0]).

start_link(File) ->
    gen_server:start_link({local, ?MODULE}, ?MODULE, File, []).

-spec create(map()) -> book().
create(Fields) -> gen_server:call(?MODULE, {create, Fields}).

-spec list() -> [book()].
list() -> list(undefined).

%% List books ordered by id, optionally only those by the given author.
-spec list(binary() | undefined) -> [book()].
list(Author) -> gen_server:call(?MODULE, {list, Author}).

-spec get(integer()) -> {ok, book()} | not_found.
get(Id) -> gen_server:call(?MODULE, {get, Id}).

-spec update(integer(), map()) -> {ok, book()} | not_found.
update(Id, Fields) -> gen_server:call(?MODULE, {update, Id, Fields}).

-spec delete(integer()) -> ok | not_found.
delete(Id) -> gen_server:call(?MODULE, {delete, Id}).

%% Remove all books and reset the id sequence.
-spec clear() -> ok.
clear() -> gen_server:call(?MODULE, clear).

init(File) ->
    process_flag(trap_exit, true),
    ok = filelib:ensure_dir(File),
    {ok, ?TABLE} = dets:open_file(?TABLE, [{file, File}, {type, set}]),
    {ok, #{}}.

handle_call({create, Fields}, _From, State) ->
    Id = next_id(),
    Book = Fields#{id => Id},
    ok = dets:insert(?TABLE, {Id, Book}),
    ok = dets:sync(?TABLE),
    {reply, Book, State};
handle_call({list, Author}, _From, State) ->
    Books = dets:foldl(
        fun
            ({Id, Book}, Acc) when is_integer(Id) ->
                case Author =:= undefined orelse maps:get(author, Book) =:= Author of
                    true -> [Book | Acc];
                    false -> Acc
                end;
            (_, Acc) ->
                Acc
        end,
        [],
        ?TABLE
    ),
    Sorted = lists:sort(fun(#{id := A}, #{id := B}) -> A =< B end, Books),
    {reply, Sorted, State};
handle_call({get, Id}, _From, State) ->
    {reply, lookup(Id), State};
handle_call({update, Id, Fields}, _From, State) ->
    Reply =
        case lookup(Id) of
            {ok, _} ->
                Book = Fields#{id => Id},
                ok = dets:insert(?TABLE, {Id, Book}),
                ok = dets:sync(?TABLE),
                {ok, Book};
            not_found ->
                not_found
        end,
    {reply, Reply, State};
handle_call({delete, Id}, _From, State) ->
    Reply =
        case lookup(Id) of
            {ok, _} ->
                ok = dets:delete(?TABLE, Id),
                ok = dets:sync(?TABLE);
            not_found ->
                not_found
        end,
    {reply, Reply, State};
handle_call(clear, _From, State) ->
    ok = dets:delete_all_objects(?TABLE),
    {reply, ok, State}.

handle_cast(_Msg, State) ->
    {noreply, State}.

terminate(_Reason, _State) ->
    dets:close(?TABLE).

lookup(Id) when is_integer(Id) ->
    case dets:lookup(?TABLE, Id) of
        [{Id, Book}] -> {ok, Book};
        [] -> not_found
    end.

%% Ids are never reused: the counter lives in the table alongside the books.
next_id() ->
    case dets:lookup(?TABLE, ?COUNTER) of
        [] -> ok = dets:insert(?TABLE, {?COUNTER, 0});
        _ -> ok
    end,
    dets:update_counter(?TABLE, ?COUNTER, 1).
