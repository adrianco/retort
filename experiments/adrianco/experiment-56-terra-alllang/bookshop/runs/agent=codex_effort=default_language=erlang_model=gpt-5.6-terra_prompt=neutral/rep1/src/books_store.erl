-module(books_store).
-behaviour(gen_server).

-export([start_link/1, stop/0, create/1, list/1, get/1, update/2, delete/1]).
-export([init/1, handle_call/3, terminate/2, code_change/3, handle_cast/2, handle_info/2]).

start_link(File) -> gen_server:start_link({local, ?MODULE}, ?MODULE, [File], []).
stop() -> gen_server:call(?MODULE, stop).
create(Book) -> gen_server:call(?MODULE, {create, Book}).
list(Author) -> gen_server:call(?MODULE, {list, Author}).
get(Id) -> gen_server:call(?MODULE, {get, Id}).
update(Id, Book) -> gen_server:call(?MODULE, {update, Id, Book}).
delete(Id) -> gen_server:call(?MODULE, {delete, Id}).

init([File]) ->
    ok = ensure_directory(File),
    {ok, ?MODULE} = dets:open_file(?MODULE, [{file, File}, {type, set}]),
    {ok, #{}}.

handle_call({create, Book0}, _From, State) ->
    Id = next_id(), Book = Book0#{id => Id}, ok = dets:insert(?MODULE, {Id, Book}),
    {reply, {ok, Book}, State};
handle_call({list, Author}, _From, State) ->
    Books = dets:foldl(fun({Id, B}, Acc) when is_integer(Id) -> [B | Acc]; (_, Acc) -> Acc end, [], ?MODULE),
    Filtered = case Author of undefined -> Books; _ -> [B || B <- Books, maps:get(author, B) =:= Author] end,
    {reply, {ok, lists:sort(fun(A, B) -> maps:get(id, A) < maps:get(id, B) end, Filtered)}, State};
handle_call({get, Id}, _From, State) ->
    Reply = case dets:lookup(?MODULE, Id) of [{Id, Book}] -> {ok, Book}; [] -> not_found end,
    {reply, Reply, State};
handle_call({update, Id, Changes}, _From, State) ->
    Reply = case dets:lookup(?MODULE, Id) of
        [{Id, Existing}] -> Book = maps:merge(Existing, Changes#{id => Id}), ok = dets:insert(?MODULE, {Id, Book}), {ok, Book};
        [] -> not_found
    end,
    {reply, Reply, State};
handle_call({delete, Id}, _From, State) ->
    Reply = case dets:lookup(?MODULE, Id) of
        [] -> not_found;
        [_] -> ok = dets:delete(?MODULE, Id), ok
    end,
    {reply, Reply, State};
handle_call(stop, _From, State) -> {stop, normal, ok, State};
handle_call(_, _From, State) -> {reply, {error, bad_request}, State}.

handle_cast(_, State) -> {noreply, State}.
handle_info(_, State) -> {noreply, State}.
terminate(_, _) ->
    try dets:close(?MODULE) catch _:_ -> ok end,
    ok.
code_change(_, State, _) -> {ok, State}.

next_id() ->
    case dets:lookup(?MODULE, '$next_id') of
        [{'$next_id', Id}] -> ok = dets:insert(?MODULE, {'$next_id', Id + 1}), Id;
        [] -> ok = dets:insert(?MODULE, {'$next_id', 2}), 1
    end.

ensure_directory(File) ->
    case filename:dirname(File) of "." -> ok; Dir -> filelib:ensure_dir(filename:join(Dir, "placeholder")) end.
