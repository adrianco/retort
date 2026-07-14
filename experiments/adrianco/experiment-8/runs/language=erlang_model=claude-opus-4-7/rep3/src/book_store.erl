-module(book_store).

-export([init/0, close/0, create/1, list/0, list/1, find/1, update/2, delete/1]).

-define(TABLE, books).
-define(COUNTER_KEY, '$counter').

init() ->
    DbFile = application:get_env(book_api, db_file, "books.dets"),
    {ok, ?TABLE} = dets:open_file(?TABLE, [{file, DbFile}, {type, set}]),
    case dets:lookup(?TABLE, ?COUNTER_KEY) of
        [] -> dets:insert(?TABLE, {?COUNTER_KEY, 0});
        _  -> ok
    end,
    ok.

close() ->
    case dets:info(?TABLE) of
        undefined -> ok;
        _ -> dets:close(?TABLE)
    end.

next_id() ->
    [{_, N}] = dets:lookup(?TABLE, ?COUNTER_KEY),
    NewN = N + 1,
    ok = dets:insert(?TABLE, {?COUNTER_KEY, NewN}),
    NewN.

create(Book) when is_map(Book) ->
    Id = next_id(),
    Full = Book#{id => Id},
    ok = dets:insert(?TABLE, {Id, Full}),
    Full.

list() ->
    dets:foldl(
      fun({Id, Book}, Acc) when is_integer(Id) -> [Book | Acc];
         (_,                Acc)                -> Acc
      end, [], ?TABLE).

list(Author) when is_binary(Author) ->
    [Book || Book <- list(), maps:get(author, Book, undefined) =:= Author].

find(Id) when is_integer(Id) ->
    case dets:lookup(?TABLE, Id) of
        [{Id, Book}] -> {ok, Book};
        []           -> {error, not_found}
    end.

update(Id, Updates) when is_integer(Id), is_map(Updates) ->
    case find(Id) of
        {ok, Existing} ->
            Merged = maps:merge(Existing, Updates#{id => Id}),
            ok = dets:insert(?TABLE, {Id, Merged}),
            {ok, Merged};
        Error ->
            Error
    end.

delete(Id) when is_integer(Id) ->
    case dets:lookup(?TABLE, Id) of
        [{Id, _}] ->
            ok = dets:delete(?TABLE, Id),
            ok;
        [] ->
            {error, not_found}
    end.
