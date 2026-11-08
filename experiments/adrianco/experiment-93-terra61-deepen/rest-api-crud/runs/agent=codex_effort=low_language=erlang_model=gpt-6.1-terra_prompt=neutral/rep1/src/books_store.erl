-module(books_store).
-behaviour(gen_server).
-export([start_link/0, list/1, get/1, create/1, update/2, delete/1]).
-export([init/1, handle_call/3, handle_cast/2, handle_info/2, terminate/2]).
start_link() -> gen_server:start_link({local, ?MODULE}, ?MODULE, [], []).
list(Author) -> gen_server:call(?MODULE, {list, Author}).
get(Id) -> gen_server:call(?MODULE, {get, Id}).
create(Book) -> gen_server:call(?MODULE, {create, Book}).
update(Id, Book) -> gen_server:call(?MODULE, {update, Id, Book}).
delete(Id) -> gen_server:call(?MODULE, {delete, Id}).
init([]) ->
    File = application:get_env(books, db_file, "books.dets"),
    case dets:open_file(books_data, [{file, File}, {type, set}, {auto_save, 1000}]) of
        {ok, Tab} -> {ok, Tab};
        {error, Reason} -> {stop, Reason}
    end.
handle_call({list, Author}, _, Tab) ->
    Books = dets:foldl(fun({Id, Book}, Acc) when is_integer(Id) ->
        case Author =:= undefined orelse maps:get(<<"author">>, Book) =:= Author of
            true -> [Book | Acc]; false -> Acc
        end;
        (_, Acc) -> Acc
    end, [], Tab),
    {reply, lists:sort(fun(A, B) -> maps:get(<<"id">>, A) < maps:get(<<"id">>, B) end, Books), Tab};
handle_call({get, Id}, _, Tab) -> {reply, lookup(Tab, Id), Tab};
handle_call({create, Book}, _, Tab) ->
    Id = case dets:lookup(Tab, next_id) of [{next_id, N}] -> N; [] -> 1 end,
    New = Book#{<<"id">> => Id},
    ok = dets:insert(Tab, [{next_id, Id + 1}, {Id, New}]),
    ok = dets:sync(Tab),
    {reply, {ok, New}, Tab};
handle_call({update, Id, Book}, _, Tab) ->
    case lookup(Tab, Id) of
        not_found -> {reply, not_found, Tab};
        {ok, _} ->
            New = Book#{<<"id">> => Id},
            ok = dets:insert(Tab, {Id, New}), ok = dets:sync(Tab),
            {reply, {ok, New}, Tab}
    end;
handle_call({delete, Id}, _, Tab) ->
    case lookup(Tab, Id) of
        not_found -> {reply, not_found, Tab};
        {ok, _} -> ok = dets:delete(Tab, Id), ok = dets:sync(Tab), {reply, ok, Tab}
    end.
lookup(Tab, Id) -> case dets:lookup(Tab, Id) of [{Id, Book}] -> {ok, Book}; [] -> not_found end.
handle_cast(_, State) -> {noreply, State}.
handle_info(_, State) -> {noreply, State}.
terminate(_, Tab) -> dets:close(Tab), ok.
