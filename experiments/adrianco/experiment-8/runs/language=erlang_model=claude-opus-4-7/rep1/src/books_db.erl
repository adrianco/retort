-module(books_db).

-export([init/0, close/0, create/1, get/1, list/0, list_by_author/1,
         update/2, delete/1, generate_id/0]).

-define(TABLE, books).

init() ->
    File = application:get_env(books_app, db_file, "books.dets"),
    case dets:open_file(?TABLE, [{file, File}, {type, set}]) of
        {ok, ?TABLE} -> ok;
        {error, Reason} -> {error, Reason}
    end.

close() ->
    case dets:info(?TABLE) of
        undefined -> ok;
        _ -> dets:close(?TABLE)
    end.

create(Attrs) when is_map(Attrs) ->
    Id = generate_id(),
    Book = Attrs#{<<"id">> => Id},
    ok = dets:insert(?TABLE, {Id, Book}),
    {ok, Book}.

get(Id) when is_binary(Id) ->
    case dets:lookup(?TABLE, Id) of
        [{Id, Book}] -> {ok, Book};
        [] -> {error, not_found}
    end.

list() ->
    Books = dets:foldl(fun({_Id, Book}, Acc) -> [Book | Acc] end, [], ?TABLE),
    {ok, Books}.

list_by_author(Author) when is_binary(Author) ->
    {ok, AllBooks} = list(),
    {ok, [B || B <- AllBooks, maps:get(<<"author">>, B, undefined) =:= Author]}.

update(Id, Attrs) when is_binary(Id), is_map(Attrs) ->
    case ?MODULE:get(Id) of
        {ok, Existing} ->
            Cleaned = maps:remove(<<"id">>, Attrs),
            Merged = maps:merge(Existing, Cleaned),
            Updated = Merged#{<<"id">> => Id},
            ok = dets:insert(?TABLE, {Id, Updated}),
            {ok, Updated};
        {error, not_found} ->
            {error, not_found}
    end.

delete(Id) when is_binary(Id) ->
    case dets:lookup(?TABLE, Id) of
        [_] ->
            ok = dets:delete(?TABLE, Id),
            ok;
        [] ->
            {error, not_found}
    end.

generate_id() ->
    binary:encode_hex(crypto:strong_rand_bytes(8), lowercase).
