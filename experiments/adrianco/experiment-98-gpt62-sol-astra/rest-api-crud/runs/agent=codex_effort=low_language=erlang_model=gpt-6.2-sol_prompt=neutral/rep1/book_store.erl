-module(book_store).
-behaviour(gen_server).

-export([start_link/1, stop/0, request/1]).
-export([init/1, handle_call/3, handle_cast/2, terminate/2]).

start_link(File) ->
    gen_server:start_link({local, ?MODULE}, ?MODULE, File, []).

stop() ->
    gen_server:stop(?MODULE).

request(Operation) ->
    gen_server:call(?MODULE, Operation).

init(File) ->
    case dets:open_file(books, [{file, File}, {type, set}]) of
        {ok, Table} ->
            case dets:insert_new(Table, {next_id, 0}) of
                Inserted when is_boolean(Inserted) -> {ok, Table};
                {error, Reason} ->
                    dets:close(Table),
                    {stop, Reason}
            end;
        {error, Reason} -> {stop, Reason}
    end.

handle_call(Operation, _From, Table) ->
    {reply, execute(Operation, Table), Table}.

handle_cast(_Message, Table) ->
    {noreply, Table}.

terminate(_Reason, Table) ->
    dets:close(Table).

execute(health, _Table) ->
    ok;
execute({create, Fields}, Table) ->
    Id = dets:update_counter(Table, next_id, 1),
    ok = dets:sync(Table),
    save(Table, Id, Fields);
execute({list, Author}, Table) ->
    Match = fun
        ({{book, _}, #{<<"author">> := Name} = Book}, Acc)
                when Author =:= all; Author =:= Name ->
            [Book | Acc];
        (_, Acc) ->
            Acc
    end,
    Books = dets:foldl(Match, [], Table),
    {ok, lists:sort(fun(A, B) -> maps:get(<<"id">>, A) < maps:get(<<"id">>, B) end,
                    Books)};
execute({get, Id}, Table) ->
    case dets:lookup(Table, {book, Id}) of
        [{_, Book}] -> {ok, Book};
        [] -> not_found
    end;
execute({update, Id, Fields}, Table) ->
    case execute({get, Id}, Table) of
        {ok, _} -> save(Table, Id, Fields);
        not_found -> not_found
    end;
execute({delete, Id}, Table) ->
    case execute({get, Id}, Table) of
        {ok, _} ->
            ok = dets:delete(Table, {book, Id}),
            dets:sync(Table);
        not_found -> not_found
    end.

save(Table, Id, Fields) ->
    Book = Fields#{<<"id">> => Id},
    ok = dets:insert(Table, {{book, Id}, Book}),
    ok = dets:sync(Table),
    {ok, Book}.
