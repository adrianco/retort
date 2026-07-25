%% Storage layer for books, backed by DETS (Erlang's embedded on-disk
%% key-value database). A gen_server serializes writes and id allocation.
%%
%% Objects stored in the table:
%%   {Id :: pos_integer(), Book :: map()}   -- one per book
%%   {next_id, N :: pos_integer()}          -- id counter
-module(book_store).
-behaviour(gen_server).

-export([start_link/1]).
-export([create/1, list/0, list_by_author/1, get/1, update/2, delete/1]).
-export([init/1, handle_call/3, handle_cast/2, terminate/2]).

-define(TABLE, ?MODULE).

%%% Public API ---------------------------------------------------------------

start_link(DataFile) ->
    gen_server:start_link({local, ?MODULE}, ?MODULE, DataFile, []).

-spec create(map()) -> {ok, map()}.
create(Fields) ->
    gen_server:call(?MODULE, {create, Fields}).

-spec list() -> [map()].
list() ->
    gen_server:call(?MODULE, list).

-spec list_by_author(binary()) -> [map()].
list_by_author(Author) ->
    [B || B <- list(), maps:get(author, B) =:= Author].

-spec get(pos_integer()) -> {ok, map()} | not_found.
get(Id) ->
    gen_server:call(?MODULE, {get, Id}).

-spec update(pos_integer(), map()) -> {ok, map()} | not_found.
update(Id, Fields) ->
    gen_server:call(?MODULE, {update, Id, Fields}).

-spec delete(pos_integer()) -> ok | not_found.
delete(Id) ->
    gen_server:call(?MODULE, {delete, Id}).

%%% gen_server callbacks -----------------------------------------------------

init(DataFile) ->
    {ok, ?TABLE} = dets:open_file(?TABLE, [{file, DataFile}, {type, set}]),
    case dets:lookup(?TABLE, next_id) of
        [] -> ok = dets:insert(?TABLE, {next_id, 1});
        _ -> ok
    end,
    {ok, ?TABLE}.

handle_call({create, Fields}, _From, Table) ->
    Id = dets:update_counter(Table, next_id, 1) - 1,
    Book = Fields#{id => Id},
    ok = dets:insert(Table, {Id, Book}),
    {reply, {ok, Book}, Table};
handle_call(list, _From, Table) ->
    Books = dets:foldl(fun({Id, Book}, Acc) when is_integer(Id) -> [Book | Acc];
                          (_, Acc) -> Acc
                       end, [], Table),
    {reply, lists:sort(fun(A, B) -> maps:get(id, A) =< maps:get(id, B) end, Books), Table};
handle_call({get, Id}, _From, Table) ->
    case dets:lookup(Table, Id) of
        [{Id, Book}] -> {reply, {ok, Book}, Table};
        [] -> {reply, not_found, Table}
    end;
handle_call({update, Id, Fields}, _From, Table) ->
    case dets:lookup(Table, Id) of
        [{Id, _Old}] ->
            Book = Fields#{id => Id},
            ok = dets:insert(Table, {Id, Book}),
            {reply, {ok, Book}, Table};
        [] ->
            {reply, not_found, Table}
    end;
handle_call({delete, Id}, _From, Table) ->
    case dets:lookup(Table, Id) of
        [{Id, _}] ->
            ok = dets:delete(Table, Id),
            {reply, ok, Table};
        [] ->
            {reply, not_found, Table}
    end.

handle_cast(_Msg, Table) ->
    {noreply, Table}.

terminate(_Reason, Table) ->
    dets:close(Table),
    ok.
