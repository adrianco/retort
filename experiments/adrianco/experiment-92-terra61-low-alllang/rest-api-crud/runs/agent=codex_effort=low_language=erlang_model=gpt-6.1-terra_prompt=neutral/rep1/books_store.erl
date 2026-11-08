-module(books_store).
-behaviour(gen_server).
-export([start/1, stop/0, create/1, list/1, get/1, update/2, delete/1]).
-export([init/1, handle_call/3, handle_cast/2, handle_info/2, terminate/2, code_change/3]).
start(File) -> case gen_server:start({local, ?MODULE}, ?MODULE, File, []) of {ok, _} -> ok; Error -> Error end.
stop() -> case whereis(?MODULE) of undefined -> ok; _ -> gen_server:stop(?MODULE) end.
create(Book) -> gen_server:call(?MODULE, {create, Book}).
list(Filter) -> gen_server:call(?MODULE, {list, Filter}).
get(Id) -> gen_server:call(?MODULE, {get, Id}).
update(Id, Book) -> gen_server:call(?MODULE, {update, Id, Book}).
delete(Id) -> gen_server:call(?MODULE, {delete, Id}).
init(File) ->
    case dets:open_file(books_data, [{file, File}, {type, set}]) of
        {ok, Tab} -> {ok, Tab}; Error -> {stop, Error}
    end.
handle_call({create, Book}, _, Tab) ->
    Id = case dets:lookup(Tab, next_id) of [{next_id, N}] -> N; [] -> 1 end,
    Saved = Book#{id => Id},
    ok = dets:insert(Tab, [{next_id, Id + 1}, {{book, Id}, Saved}]), ok = dets:sync(Tab),
    {reply, Saved, Tab};
handle_call({list, Filter}, _, Tab) ->
    Books = dets:foldl(fun({{book, _}, B}, Acc) ->
        case Filter =:= undefined orelse maps:get(author, B) =:= Filter of true -> [B | Acc]; false -> Acc end;
        (_, Acc) -> Acc end, [], Tab),
    {reply, lists:sort(fun(A, B) -> maps:get(id, A) < maps:get(id, B) end, Books), Tab};
handle_call({get, Id}, _, Tab) -> {reply, lookup(Tab, Id), Tab};
handle_call({update, Id, Book}, _, Tab) ->
    case lookup(Tab, Id) of
        not_found -> {reply, not_found, Tab};
        _ -> Saved = Book#{id => Id}, ok = dets:insert(Tab, {{book, Id}, Saved}), ok = dets:sync(Tab), {reply, {ok, Saved}, Tab}
    end;
handle_call({delete, Id}, _, Tab) ->
    case lookup(Tab, Id) of
        not_found -> {reply, not_found, Tab};
        _ -> ok = dets:delete(Tab, {book, Id}), ok = dets:sync(Tab), {reply, ok, Tab}
    end.
lookup(Tab, Id) -> case dets:lookup(Tab, {book, Id}) of [{{book, Id}, Book}] -> {ok, Book}; [] -> not_found end.
handle_cast(_, State) -> {noreply, State}.
handle_info(_, State) -> {noreply, State}.
terminate(_, Tab) -> dets:close(Tab).
code_change(_, State, _) -> {ok, State}.
