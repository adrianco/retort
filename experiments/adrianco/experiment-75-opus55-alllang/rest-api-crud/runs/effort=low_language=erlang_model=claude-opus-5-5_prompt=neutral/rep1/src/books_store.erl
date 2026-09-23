%% Persistence using DETS (Erlang's built-in embedded disk store).
-module(books_store).
-compile({no_auto_import,[get/1]}).
-export([open/1, close/0, create/1, list/1, get/1, update/2, delete/1]).

-define(T, books_table).

open(File) ->
    {ok, ?T} = dets:open_file(?T, [{file, File}, {type, set}]),
    ok.

close() -> dets:close(?T).

next_id() -> dets:update_counter(?T, '$counter', 1).

create(Book) ->
    Id = case dets:lookup(?T, '$counter') of
             [] -> ok = dets:insert(?T, {'$counter', 0}), next_id();
             _ -> next_id()
         end,
    B = Book#{<<"id">> => Id},
    ok = dets:insert(?T, {Id, B}),
    B.

list(Author) ->
    All = [B || {K, B} <- dets:match_object(?T, '_'), is_integer(K)],
    Filtered = case Author of
                   undefined -> All;
                   A -> [B || B = #{<<"author">> := BA} <- All, BA =:= A]
               end,
    lists:sort(fun(#{<<"id">> := X}, #{<<"id">> := Y}) -> X =< Y end, Filtered).

get(Id) ->
    case dets:lookup(?T, Id) of
        [{Id, B}] -> {ok, B};
        [] -> not_found
    end.

update(Id, Book) ->
    case get(Id) of
        {ok, _} -> B = Book#{<<"id">> => Id}, ok = dets:insert(?T, {Id, B}), {ok, B};
        not_found -> not_found
    end.

delete(Id) ->
    case get(Id) of
        {ok, _} -> ok = dets:delete(?T, Id);
        not_found -> not_found
    end.
